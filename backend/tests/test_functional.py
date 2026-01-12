import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MODULE_ORDER = [
    "database",
    "models",
    "db_models",
    "storage_service",
    "moodle_service",
    "user_service",
    "course_service",
    "grade_service",
    "activities_service",
    "lti_service",
    "activities_router",
    "submissions_router",
    "grades_router",
    "main",
]


def _reload_app_modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Reload backend modules against an isolated SQLite file and temp uploads path."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("HTTPS_ENABLED", "false")

    modules = {}
    for name in MODULE_ORDER:
        if name in sys.modules:
            modules[name] = importlib.reload(sys.modules[name])
        else:
            modules[name] = importlib.import_module(name)

    # Redirect file storage to the temp directory to keep the repo clean during tests.
    storage = modules["storage_service"].FileStorageService
    storage.BASE_DIR = str(tmp_path)
    storage.UPLOADS_ROOT = os.path.join(str(tmp_path), "uploads")

    modules["database"].init_db()
    modules["main"].lti_data_store.clear()
    return modules


@pytest.fixture
def app_ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Yield a fresh TestClient and loaded modules per test."""
    modules = _reload_app_modules(tmp_path, monkeypatch)
    app = modules["main"].app
    with TestClient(app) as client:
        yield client, modules


def _lti_payload(user_id: str, roles: str, *, resource_link_id: str = "act-001", context_id: str = "course-001", moodle_id: str = "moodle-001"):
    return {
        "lti_message_type": "basic-lti-launch-request",
        "lti_version": "LTI-1p0",
        "resource_link_id": resource_link_id,
        "resource_link_title": "Activity",
        "context_id": context_id,
        "context_title": "Course",
        "context_label": "C1",
        "user_id": user_id,
        "ext_user_username": user_id,
        "lis_person_name_given": "Test",
        "lis_person_name_family": "User",
        "lis_person_name_full": "Test User",
        "lis_person_contact_email_primary": f"{user_id}@example.com",
        "lis_result_sourcedid": f"sourced-{user_id}",
        "lis_outcome_service_url": "https://moodle.example/outcome",
        "roles": roles,
        "tool_consumer_instance_guid": moodle_id,
        "tool_consumer_instance_name": "Moodle QA",
        "launch_presentation_return_url": "https://moodle.example/return",
        "oauth_consumer_key": "key-123",
    }


def _launch_lti(client: TestClient, payload: dict) -> str:
    resp = client.post("/lti", data=payload, follow_redirects=False)
    assert resp.status_code == 303
    session_id = resp.cookies.get("lti_session")
    assert session_id
    return session_id


def test_lti_launch_stores_session_and_entities(app_ctx):
    client, modules = app_ctx
    payload = _lti_payload(user_id="teacher1", roles="Instructor")
    _launch_lti(client, payload)

    lti_resp = client.get("/api/lti-data")
    assert lti_resp.status_code == 200
    data = lti_resp.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == payload["user_id"]
    assert data["data"]["context_id"] == payload["context_id"]

    db = modules["database"].get_db_session()
    try:
        MoodleDB = modules["db_models"].MoodleDB
        UserDB = modules["db_models"].UserDB
        CourseDB = modules["db_models"].CourseDB

        moodle = db.query(MoodleDB).filter_by(id=payload["tool_consumer_instance_guid"]).first()
        user = db.query(UserDB).filter_by(id=payload["user_id"], moodle_id=payload["tool_consumer_instance_guid"]).first()
        course = db.query(CourseDB).filter_by(id=payload["context_id"], moodle_id=payload["tool_consumer_instance_guid"]).first()

        assert moodle is not None
        assert user is not None and user.role == "teacher"
        assert course is not None
    finally:
        db.close()


def test_teacher_creates_activity_from_lti_context(app_ctx):
    client, modules = app_ctx
    payload = _lti_payload(user_id="teacher2", roles="Instructor", resource_link_id="act-123", context_id="course-123", moodle_id="moodle-123")
    _launch_lti(client, payload)

    activity_body = {
        "title": "Demo Activity",
        "description": "Activity created by teacher",
        "activity_type": "individual",
        "deadline": None,
        "evaluator_id": None,
    }

    resp = client.post("/api/activities", json=activity_body)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["activity"]["id"] == payload["resource_link_id"]
    assert body["activity"]["course_id"] == payload["context_id"]

    db = modules["database"].get_db_session()
    try:
        ActivityDB = modules["db_models"].ActivityDB
        activity = db.query(ActivityDB).filter_by(id=payload["resource_link_id"], course_moodle_id=payload["tool_consumer_instance_guid"]).first()
        assert activity is not None
        assert activity.creator_id == payload["user_id"]
        assert activity.course_id == payload["context_id"]
    finally:
        db.close()


def test_student_submission_and_teacher_grading_flow(app_ctx):
    client, modules = app_ctx
    teacher_payload = _lti_payload(user_id="teacher3", roles="Instructor", resource_link_id="act-789", context_id="course-789", moodle_id="moodle-789")
    teacher_session = _launch_lti(client, teacher_payload)

    activity_body = {
        "title": "Activity to grade",
        "description": "Upload a short text",
        "activity_type": "individual",
        "deadline": None,
        "evaluator_id": None,
    }
    activity_resp = client.post("/api/activities", json=activity_body)
    assert activity_resp.status_code == 200

    student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=teacher_payload["resource_link_id"], context_id=teacher_payload["context_id"], moodle_id=teacher_payload["tool_consumer_instance_guid"])
    _launch_lti(client, student_payload)

    submission_resp = client.post(
        f"/api/activities/{teacher_payload['resource_link_id']}/submissions",
        files={"file": ("hello.txt", b"Hello world", "text/plain")},
    )
    assert submission_resp.status_code == 200
    submission_body = submission_resp.json()
    assert submission_body["success"] is True
    file_submission_id = submission_body["submission"]["file_submission"]["id"]

    client.cookies.set("lti_session", teacher_session)
    grade_resp = client.post(
        f"/api/grades/{file_submission_id}",
        json={"score": 9.5, "comment": "Great job"},
    )
    assert grade_resp.status_code == 200
    grade_body = grade_resp.json()
    assert grade_body["success"] is True
    assert grade_body["grade"]["score"] == 9.5

    db = modules["database"].get_db_session()
    try:
        GradeDB = modules["db_models"].GradeDB
        grade = db.query(GradeDB).filter_by(file_submission_id=file_submission_id).first()
        assert grade is not None
        assert grade.score == 9.5
    finally:
        db.close()


def test_group_code_capacity_enforced(app_ctx):
    client, modules = app_ctx

    teacher_payload = _lti_payload(
        user_id="teacher4",
        roles="Instructor",
        resource_link_id="act-group",
        context_id="course-group",
        moodle_id="moodle-group",
    )
    teacher_session = _launch_lti(client, teacher_payload)

    activity_body = {
        "title": "Group Activity",
        "description": "Group work",
        "activity_type": "group",
        "max_group_size": 2,
        "deadline": None,
        "evaluator_id": None,
    }
    resp = client.post("/api/activities", json=activity_body)
    assert resp.status_code == 200

    # Student leader creates initial submission and group code
    student1_payload = _lti_payload(
        user_id="student2",
        roles="Learner",
        resource_link_id="act-group",
        context_id="course-group",
        moodle_id="moodle-group",
    )
    _launch_lti(client, student1_payload)

    submission_resp = client.post(
        "/api/activities/act-group/submissions",
        files={"file": ("group.txt", b"group work", "text/plain")},
    )
    assert submission_resp.status_code == 200
    group_code = submission_resp.json()["submission"]["file_submission"]["group_code"]
    assert group_code

    # Second student joins successfully
    student2_payload = _lti_payload(
        user_id="student3",
        roles="Learner",
        resource_link_id="act-group",
        context_id="course-group",
        moodle_id="moodle-group",
    )
    _launch_lti(client, student2_payload)
    join_resp_ok = client.post(
        "/api/submissions/join",
        json={"activity_id": "act-group", "group_code": group_code},
    )
    assert join_resp_ok.status_code == 200
    assert join_resp_ok.json()["success"] is True

    # Third student should be rejected because capacity is 2
    student3_payload = _lti_payload(
        user_id="student4",
        roles="Learner",
        resource_link_id="act-group",
        context_id="course-group",
        moodle_id="moodle-group",
    )
    _launch_lti(client, student3_payload)
    join_resp_full = client.post(
        "/api/submissions/join",
        json={"activity_id": "act-group", "group_code": group_code},
    )
    assert join_resp_full.status_code == 400
    assert "maximum number of uses" in join_resp_full.json()["detail"].lower()


def test_group_code_requires_student_role(app_ctx):
    client, modules = app_ctx

    # Create activity as teacher
    teacher_payload = _lti_payload(
        user_id="teacher5",
        roles="Instructor",
        resource_link_id="act-role",
        context_id="course-role",
        moodle_id="moodle-role",
    )
    _launch_lti(client, teacher_payload)
    activity_body = {
        "title": "Group Activity",
        "description": "Group work",
        "activity_type": "group",
        "max_group_size": 3,
        "deadline": None,
        "evaluator_id": None,
    }
    create_resp = client.post("/api/activities", json=activity_body)
    assert create_resp.status_code == 200

    # Student leader submits to get a group code
    student_payload = _lti_payload(
        user_id="student5",
        roles="Learner",
        resource_link_id="act-role",
        context_id="course-role",
        moodle_id="moodle-role",
    )
    _launch_lti(client, student_payload)
    submission_resp = client.post(
        "/api/activities/act-role/submissions",
        files={"file": ("group2.txt", b"group work", "text/plain")},
    )
    assert submission_resp.status_code == 200
    group_code = submission_resp.json()["submission"]["file_submission"]["group_code"]
    assert group_code

    # Teacher (non-student) tries to join a group and should be forbidden
    _launch_lti(client, teacher_payload)
    join_resp = client.post(
        "/api/submissions/join",
        json={"activity_id": "act-role", "group_code": group_code},
    )
    assert join_resp.status_code == 403
    assert "solo estudiantes" in join_resp.json()["detail"].lower()


def test_student_cannot_update_activity(app_ctx):
    client, modules = app_ctx

    teacher_payload = _lti_payload(
        user_id="teacher6",
        roles="Instructor",
        resource_link_id="act-edit",
        context_id="course-edit",
        moodle_id="moodle-edit",
    )
    _launch_lti(client, teacher_payload)

    activity_body = {
        "title": "Editable Activity",
        "description": "Initial desc",
        "activity_type": "individual",
        "deadline": None,
        "evaluator_id": None,
    }
    create_resp = client.post("/api/activities", json=activity_body)
    assert create_resp.status_code == 200

    # Student tries to update
    student_payload = _lti_payload(
        user_id="student6",
        roles="Learner",
        resource_link_id="act-edit",
        context_id="course-edit",
        moodle_id="moodle-edit",
    )
    _launch_lti(client, student_payload)
    update_resp = client.put(
        "/api/activities/act-edit",
        json={"description": "Hacked desc"},
    )
    assert update_resp.status_code == 403


def test_student_cannot_view_activity_submissions(app_ctx):
    client, modules = app_ctx

    teacher_payload = _lti_payload(
        user_id="teacher7",
        roles="Instructor",
        resource_link_id="act-list",
        context_id="course-list",
        moodle_id="moodle-list",
    )
    _launch_lti(client, teacher_payload)

    activity_body = {
        "title": "List Activity",
        "description": "Check submissions",
        "activity_type": "individual",
        "deadline": None,
        "evaluator_id": None,
    }
    create_resp = client.post("/api/activities", json=activity_body)
    assert create_resp.status_code == 200

    student_payload = _lti_payload(
        user_id="student7",
        roles="Learner",
        resource_link_id="act-list",
        context_id="course-list",
        moodle_id="moodle-list",
    )
    _launch_lti(client, student_payload)

    list_resp = client.get("/api/activities/act-list/submissions")
    assert list_resp.status_code == 403


def test_student_cannot_create_activity(app_ctx):
    client, modules = app_ctx

    student_payload = _lti_payload(
        user_id="student8",
        roles="Learner",
        resource_link_id="act-create",
        context_id="course-create",
        moodle_id="moodle-create",
    )
    _launch_lti(client, student_payload)

    activity_body = {
        "title": "Should fail",
        "description": "Students cannot create",
        "activity_type": "individual",
        "deadline": None,
        "evaluator_id": None,
    }
    resp = client.post("/api/activities", json=activity_body)
    assert resp.status_code == 403


def test_join_group_invalid_code_returns_400(app_ctx):
    client, modules = app_ctx

    # Prepare context with a group activity
    teacher_payload = _lti_payload(
        user_id="teacher9",
        roles="Instructor",
        resource_link_id="act-invalid",
        context_id="course-invalid",
        moodle_id="moodle-invalid",
    )
    _launch_lti(client, teacher_payload)
    activity_body = {
        "title": "Group Invalid Code",
        "description": "",
        "activity_type": "group",
        "max_group_size": 2,
        "deadline": None,
        "evaluator_id": None,
    }
    create_resp = client.post("/api/activities", json=activity_body)
    assert create_resp.status_code == 200

    # Student tries to join with non-existent code
    student_payload = _lti_payload(
        user_id="student9",
        roles="Learner",
        resource_link_id="act-invalid",
        context_id="course-invalid",
        moodle_id="moodle-invalid",
    )
    _launch_lti(client, student_payload)
    join_resp = client.post(
        "/api/submissions/join",
        json={"activity_id": "act-invalid", "group_code": "ZZZZZZZZ"},
    )
    assert join_resp.status_code == 400
    assert "invalid group code" in join_resp.json()["detail"].lower()
