"""
Pruebas comprehensivas de todos los endpoints de la API LAMBA.
Incluye casos de éxito y error para cada endpoint.

Estructura de pruebas:
- Autenticación LTI
- Actividades (CRUD)
- Entregas (Submissions)
- Calificaciones (Grades)
- Autorización y permisos
- Validación de datos
"""

import importlib
import os
import sys
from pathlib import Path
import io
import json

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


def _lti_payload(
    user_id: str,
    roles: str,
    *,
    resource_link_id: str = "act-001",
    context_id: str = "course-001",
    moodle_id: str = "moodle-001",
    lis_result_sourcedid: str = "sourced-001",
):
    """Create a valid LTI payload"""
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
        "lis_result_sourcedid": lis_result_sourcedid,
        "lis_outcome_service_url": "https://moodle.example/outcome",
        "roles": roles,
        "tool_consumer_instance_guid": moodle_id,
        "tool_consumer_instance_name": "Moodle QA",
        "launch_presentation_return_url": "https://moodle.example/return",
        "oauth_consumer_key": "key-123",
    }


def _launch_lti(client: TestClient, payload: dict) -> str:
    """Launch LTI and return session ID"""
    resp = client.post("/lti", data=payload, follow_redirects=False)
    assert resp.status_code == 303
    session_id = resp.cookies.get("lti_session")
    assert session_id
    return session_id


# =====================================================================
# PRUEBAS DE AUTENTICACIÓN LTI
# =====================================================================

class TestLTIAuthentication:
    """Tests for LTI authentication and /lti endpoint"""

    def test_lti_launch_success(self, app_ctx):
        """POST /lti - Caso éxito: lanzamiento LTI válido"""
        client, modules = app_ctx
        payload = _lti_payload(user_id="teacher1", roles="Instructor")
        resp = client.post("/lti", data=payload, follow_redirects=False)

        assert resp.status_code == 303
        assert resp.cookies.get("lti_session")

    def test_lti_launch_missing_required_field(self, app_ctx):
        """POST /lti - Caso error: faltan campos requeridos"""
        client, modules = app_ctx
        payload = _lti_payload(user_id="teacher1", roles="Instructor")
        del payload["user_id"]  # Eliminar campo requerido

        resp = client.post("/lti", data=payload, follow_redirects=False)
        # El servidor debe manejar esto (puede ser redirección o error)
        assert resp.status_code in [303, 400]

    def test_get_lti_data_success(self, app_ctx):
        """GET /api/lti-data - Caso éxito: obtener datos de sesión LTI"""
        client, modules = app_ctx
        payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, payload)

        resp = client.get("/api/lti-data")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "teacher1"

    def test_get_lti_data_no_session(self, app_ctx):
        """GET /api/lti-data - Caso error: sin sesión LTI"""
        client, modules = app_ctx
        # No lanzar LTI, sin sesión

        resp = client.get("/api/lti-data")
        assert resp.status_code == 401
        assert "sesión lti activa".casefold() in resp.json()["detail"].casefold()

    def test_get_lti_data_expired_session(self, app_ctx):
        """GET /api/lti-data - Caso error: sesión expirada"""
        client, modules = app_ctx
        # Establecer una cookie inválida
        client.cookies.set("lti_session", "invalid-session-id")

        resp = client.get("/api/lti-data")
        assert resp.status_code == 404


# =====================================================================
# PRUEBAS DE ACTIVIDADES (CRUD)
# =====================================================================

class TestActivitiesCreate:
    """Tests for creating activities"""

    def test_create_activity_success_individual(self, app_ctx):
        """POST /api/activities - Caso éxito: crear actividad individual"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        activity_body = {
            "title": "Práctica 1",
            "description": "Primera práctica",
            "activity_type": "individual",
            "deadline": None,
            "evaluator_id": None,
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["activity"]["title"] == "Práctica 1"
        assert data["activity"]["activity_type"] == "individual"

    def test_create_activity_success_group(self, app_ctx):
        """POST /api/activities - Caso éxito: crear actividad grupal"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        activity_body = {
            "title": "Trabajo Grupal",
            "description": "Actividad de grupo",
            "activity_type": "group",
            "max_group_size": 3,
            "deadline": None,
            "evaluator_id": None,
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["activity"]["activity_type"] == "group"
        assert data["activity"]["max_group_size"] == 3

    def test_create_activity_student_forbidden(self, app_ctx):
        """POST /api/activities - Caso error: estudiante intenta crear"""
        client, modules = app_ctx
        student_payload = _lti_payload(user_id="student1", roles="Learner")
        _launch_lti(client, student_payload)

        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 403
        assert "profesores" in resp.json()["detail"].lower()

    def test_create_activity_invalid_type(self, app_ctx):
        """POST /api/activities - Caso error: tipo de actividad inválido"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "invalid_type",
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 422  # Validation error

    def test_create_activity_group_without_max_size(self, app_ctx):
        """POST /api/activities - Caso error: actividad grupal sin max_group_size"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        activity_body = {
            "title": "Trabajo Grupal",
            "description": "Sin max_group_size",
            "activity_type": "group",
            # Falta max_group_size
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code in [400, 422]

    def test_create_activity_group_invalid_max_size(self, app_ctx):
        """POST /api/activities - Caso error: max_group_size menor a 2"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        activity_body = {
            "title": "Trabajo Grupal",
            "description": "max_group_size < 2",
            "activity_type": "group",
            "max_group_size": 1,
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 400

    def test_create_activity_no_session(self, app_ctx):
        """POST /api/activities - Caso error: sin sesión LTI"""
        client, modules = app_ctx

        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }

        resp = client.post("/api/activities", json=activity_body)
        assert resp.status_code == 401


class TestActivitiesRetrieve:
    """Tests for retrieving activities"""

    def test_get_activity_success(self, app_ctx):
        """GET /api/activities/{activity_id} - Caso éxito: obtener actividad"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad Test",
            "description": "Descripción",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Obtener actividad
        resp = client.get(f"/api/activities/{activity_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Actividad Test"

    def test_get_activity_not_found(self, app_ctx):
        """GET /api/activities/{activity_id} - Caso error: actividad no existe"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.get("/api/activities/nonexistent-id")
        assert resp.status_code == 404
        assert "no encontrada" in resp.json()["detail"].lower()

    def test_get_activity_student_forbidden(self, app_ctx):
        """GET /api/activities/{activity_id} - Caso error: estudiante no puede ver"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Intentar obtener como estudiante
        student_payload = _lti_payload(
            user_id="student1",
            roles="Learner",
            resource_link_id="act-001",
        )
        _launch_lti(client, student_payload)

        resp = client.get(f"/api/activities/{activity_id}")
        assert resp.status_code == 403

    def test_get_activity_view_student_success(self, app_ctx):
        """GET /api/activities/{activity_id}/view - Caso éxito: vista de estudiante"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-002")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad Vista",
            "description": "Para vista de estudiante",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Acceder como estudiante
        student_payload = _lti_payload(
            user_id="student1",
            roles="Learner",
            resource_link_id=activity_id,
        )
        _launch_lti(client, student_payload)

        resp = client.get(f"/api/activities/{activity_id}/view")
        assert resp.status_code == 200
        data = resp.json()
        assert "activity" in data
        assert "can_submit" in data

    def test_get_activity_view_teacher_forbidden(self, app_ctx):
        """GET /api/activities/{activity_id}/view - Caso error: profesor no puede usar vista"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.get("/api/activities/any-id/view")
        assert resp.status_code == 403

    def test_get_activity_submissions_success(self, app_ctx):
        """GET /api/activities/{activity_id}/submissions - Caso éxito: listar entregas"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-003")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Obtener entregas (vacío inicialmente)
        resp = client.get(f"/api/activities/{activity_id}/submissions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_type"] == "individual"
        assert data["total_submissions"] == 0
        assert data["submissions"] == []

    def test_get_activity_submissions_student_forbidden(self, app_ctx):
        """GET /api/activities/{activity_id}/submissions - Caso error: estudiante no puede ver"""
        client, modules = app_ctx
        student_payload = _lti_payload(user_id="student1", roles="Learner")
        _launch_lti(client, student_payload)

        resp = client.get("/api/activities/any-id/submissions")
        assert resp.status_code == 403


class TestActivitiesUpdate:
    """Tests for updating activities"""

    def test_update_activity_success(self, app_ctx):
        """PUT /api/activities/{activity_id} - Caso éxito: actualizar actividad"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad Original",
            "description": "Original",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Actualizar
        update_body = {
            "description": "Descripción actualizada",
        }
        resp = client.put(f"/api/activities/{activity_id}", json=update_body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "actualizada" in data["message"].lower()

    def test_update_activity_different_course(self, app_ctx):
        """PUT /api/activities/{activity_id} - Caso error: otro profesor de otro curso intenta actualizar"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-004")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Original",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Intentar actualizar como otro profesor desde otro curso
        other_teacher_payload = _lti_payload(
            user_id="teacher2",
            roles="Instructor",
            resource_link_id="act-004",
            context_id="course-002"  # Diferente curso
        )
        _launch_lti(client, other_teacher_payload)

        update_body = {"description": "Intento de hack"}
        resp = client.put(f"/api/activities/{activity_id}", json=update_body)
        assert resp.status_code in [400, 403]

    def test_update_activity_student_forbidden(self, app_ctx):
        """PUT /api/activities/{activity_id} - Caso error: estudiante intenta actualizar"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Original",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Intentar actualizar como estudiante
        student_payload = _lti_payload(user_id="student1", roles="Learner")
        _launch_lti(client, student_payload)

        update_body = {"description": "Hack"}
        resp = client.put(f"/api/activities/{activity_id}", json=update_body)
        assert resp.status_code == 403


# =====================================================================
# PRUEBAS DE ENTREGAS (SUBMISSIONS)
# =====================================================================

class TestSubmissionsCreate:
    """Tests for creating submissions"""

    def test_create_submission_individual_success(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Caso éxito: entrega individual"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-sub-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad Individual",
            "description": "Para entregas",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega
        student_payload = _lti_payload(
            user_id="student1",
            roles="Learner",
            resource_link_id=activity_id,
        )
        _launch_lti(client, student_payload)

        resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "file_submission" in data["submission"]

    def test_create_submission_group_leader_success(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Caso éxito: líder de grupo"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-sub-002")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Actividad Grupal",
            "description": "Para entregas de grupo",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega
        student_payload = _lti_payload(
            user_id="student1",
            roles="Learner",
            resource_link_id=activity_id,
        )
        _launch_lti(client, student_payload)

        resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Group work", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["submission"]["is_group_leader"] is True
        assert "group_code" in data["submission"]["file_submission"]

    def test_create_submission_teacher_forbidden(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Caso error: profesor intenta"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.post(
            "/api/activities/any-id/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        assert resp.status_code == 403

    def test_create_submission_missing_file(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Caso error: falta archivo"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-sub-003")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante intenta enviar sin archivo
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp = client.post(f"/api/activities/{activity_id}/submissions")
        assert resp.status_code in [400, 422]

    def test_create_submission_file_too_large(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Caso error: archivo muy grande"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-sub-004")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Descripción",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante intenta enviar archivo > 50MB
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        large_content = b"x" * (51 * 1024 * 1024)  # 51 MB
        resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("large.bin", large_content, "application/octet-stream")},
        )
        assert resp.status_code == 413 or resp.status_code == 400


class TestSubmissionsJoinGroup:
    """Tests for joining groups"""

    def test_join_group_success(self, app_ctx):
        """POST /api/submissions/join - Caso éxito: unirse a grupo"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-join-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Actividad Grupal",
            "description": "Para prueba de join",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Líder crea grupo
        leader_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, leader_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        group_code = sub_resp.json()["submission"]["file_submission"]["group_code"]

        # Otro estudiante se une
        member_payload = _lti_payload(user_id="student2", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member_payload)

        resp = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "submission" in data

    def test_join_group_invalid_code(self, app_ctx):
        """POST /api/submissions/join - Caso error: código inválido"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-join-002")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Actividad Grupal",
            "description": "Para prueba de código inválido",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante intenta unirse con código inválido
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": "INVALID"},
        )
        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower()

    def test_join_group_exceeds_capacity(self, app_ctx):
        """POST /api/submissions/join - Caso error: excede capacidad del grupo"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-join-002")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal con max_group_size=2
        activity_body = {
            "title": "Grupo Pequeño",
            "description": "Máximo 2 personas",
            "activity_type": "group",
            "max_group_size": 2,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Líder crea grupo
        leader_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, leader_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        group_code = sub_resp.json()["submission"]["file_submission"]["group_code"]

        # Segundo estudiante se une (OK)
        member2_payload = _lti_payload(user_id="student2", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member2_payload)

        resp2 = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )
        assert resp2.status_code == 200

        # Tercer estudiante intenta unirse (FALLA)
        member3_payload = _lti_payload(user_id="student3", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member3_payload)

        resp3 = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )
        assert resp3.status_code == 400
        assert "maximum" in resp3.json()["detail"].lower()

    def test_join_group_teacher_forbidden(self, app_ctx):
        """POST /api/submissions/join - Caso error: profesor no puede unirse"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.post(
            "/api/submissions/join",
            json={"activity_id": "any-id", "group_code": "CODE"},
        )
        assert resp.status_code == 403

    def test_join_group_already_member(self, app_ctx):
        """POST /api/submissions/join - Caso error: ya es miembro del grupo"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-join-003")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Grupo",
            "description": "Test",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Líder crea grupo
        leader_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, leader_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        group_code = sub_resp.json()["submission"]["file_submission"]["group_code"]

        # Segundo estudiante se une
        member_payload = _lti_payload(user_id="student2", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member_payload)

        client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )

        # Intenta unirse de nuevo
        resp = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )
        assert resp.status_code == 400


class TestSubmissionsRetrieve:
    """Tests for retrieving submissions"""

    def test_get_my_submission_success(self, app_ctx):
        """GET /api/submissions/me - Caso éxito: obtener mi entrega"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-me-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )

        # Obtener mi entrega
        resp = client.get("/api/submissions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None

    def test_get_my_submission_no_submission(self, app_ctx):
        """GET /api/submissions/me - Caso éxito: sin entrega aún (null)"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-me-002")
        _launch_lti(client, teacher_payload)

        # Crear actividad pero sin entregarla
        activity_body = {
            "title": "Actividad",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante entra pero sin entregar
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp = client.get("/api/submissions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data is None

    def test_get_my_submission_teacher_forbidden(self, app_ctx):
        """GET /api/submissions/me - Caso error: profesor no puede usar"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.get("/api/submissions/me")
        assert resp.status_code == 403

    def test_get_submission_members_success(self, app_ctx):
        """GET /api/submissions/{submission_id}/members - Caso éxito: listar miembros"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-members-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Grupo",
            "description": "Test miembros",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Líder crea grupo
        leader_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, leader_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        submission_id = sub_resp.json()["submission"]["file_submission"]["id"]

        # Otro estudiante se une
        member_payload = _lti_payload(user_id="student2", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member_payload)

        group_code = sub_resp.json()["submission"]["file_submission"]["group_code"]
        client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code},
        )

        # Obtener miembros
        resp = client.get(f"/api/submissions/{submission_id}/members")
        assert resp.status_code == 200
        members = resp.json()
        assert len(members) >= 2
        assert members[0]["is_group_leader"] is True


# =====================================================================
# PRUEBAS DE CALIFICACIONES (GRADES)
# =====================================================================

class TestGrades:
    """Tests for grading functionality"""

    def test_grade_submission_success(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso éxito: calificar entrega"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-grade-001")
        teacher_session = _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad para calificar",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        submission_id = sub_resp.json()["submission"]["file_submission"]["id"]

        # Profesor califica
        client.cookies.set("lti_session", teacher_session)
        resp = client.post(
            f"/api/grades/{submission_id}",
            json={"score": 8.5, "comment": "Buen trabajo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["grade"]["score"] == 8.5

    def test_grade_submission_invalid_score_negative(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso error: puntuación negativa"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.post(
            "/api/grades/some-id",
            json={"score": -1, "comment": "Invalid"},
        )
        assert resp.status_code == 400
        assert "debe estar entre 0 y 10" in resp.json()["detail"].lower()

    def test_grade_submission_invalid_score_too_high(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso error: puntuación > 10"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.post(
            "/api/grades/some-id",
            json={"score": 15, "comment": "Too high"},
        )
        assert resp.status_code == 400

    def test_grade_submission_student_forbidden(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso error: estudiante no puede calificar"""
        client, modules = app_ctx
        student_payload = _lti_payload(user_id="student1", roles="Learner")
        _launch_lti(client, student_payload)

        resp = client.post(
            "/api/grades/some-id",
            json={"score": 8.5, "comment": "Try to grade"},
        )
        assert resp.status_code == 403

    def test_grade_submission_nonexistent(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso error: entrega no existe"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        resp = client.post(
            "/api/grades/nonexistent-id",
            json={"score": 8.5, "comment": "Comment"},
        )
        assert resp.status_code == 404

    def test_grade_submission_update_existing(self, app_ctx):
        """POST /api/grades/{submission_id} - Caso éxito: actualizar calificación"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-grade-002")
        teacher_session = _launch_lti(client, teacher_payload)

        # Crear actividad y entrega
        activity_body = {
            "title": "Actividad",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        submission_id = sub_resp.json()["submission"]["file_submission"]["id"]

        # Primera calificación
        client.cookies.set("lti_session", teacher_session)
        client.post(
            f"/api/grades/{submission_id}",
            json={"score": 7.0, "comment": "First grade"},
        )

        # Actualizar calificación
        resp = client.post(
            f"/api/grades/{submission_id}",
            json={"score": 9.0, "comment": "Updated grade"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["grade"]["score"] == 9.0


# =====================================================================
# PRUEBAS DE VALIDACIÓN Y CASOS ESPECIALES
# =====================================================================

class TestValidationAndEdgeCases:
    """Tests for validation and edge cases"""

    def test_missing_lti_session_returns_401(self, app_ctx):
        """Todos los endpoints protegidos retornan 401 sin sesión LTI"""
        client, modules = app_ctx

        endpoints = [
            ("GET", "/api/activities/any-id"),
            ("POST", "/api/activities", {"title": "Test", "description": "Test", "activity_type": "individual"}),
            ("POST", "/api/submissions/join", {"activity_id": "any", "group_code": "CODE"}),
            ("GET", "/api/submissions/me"),
        ]

        for method, endpoint, *body_data in endpoints:
            if method == "GET":
                resp = client.get(endpoint)
            else:
                json_body = body_data[0] if body_data else None
                resp = client.post(endpoint, json=json_body)

            assert resp.status_code == 401, f"Expected 401 for {method} {endpoint}"

    def test_activity_type_case_sensitivity(self, app_ctx):
        """Tipos de actividad son case-insensitive o fijos"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor")
        _launch_lti(client, teacher_payload)

        # Intentar con mayúsculas
        activity_body = {
            "title": "Test",
            "description": "Test",
            "activity_type": "INDIVIDUAL",
        }

        resp = client.post("/api/activities", json=activity_body)
        # Puede ser 422 (validation error) o acepta ambas formas
        assert resp.status_code in [200, 422]

    def test_concurrent_submissions_same_student_individual(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Estudiante reenvía en actividad individual"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-concurrent-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad individual
        activity_body = {
            "title": "Actividad",
            "description": "Test resubmit",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea primera entrega
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp1 = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("first.txt", b"First content", "text/plain")},
        )
        assert resp1.status_code == 200

        # Estudiante reenvía (reemplaza)
        resp2 = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("second.txt", b"Second content", "text/plain")},
        )
        assert resp2.status_code == 200
        # Debe ser la misma entrega pero con archivo actualizado
        assert resp2.json()["submission"]["file_submission"]["id"] == resp1.json()["submission"]["file_submission"]["id"]

    def test_submission_with_special_characters_filename(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Nombre archivo con caracteres especiales"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-special-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega con nombre especial
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("documento_con_acentos_ñ.txt", b"Content", "text/plain")},
        )
        assert resp.status_code == 200

    def test_empty_file_submission(self, app_ctx):
        """POST /api/activities/{activity_id}/submissions - Archivo vacío"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-empty-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad
        activity_body = {
            "title": "Actividad",
            "description": "Test",
            "activity_type": "individual",
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Estudiante crea entrega vacía
        student_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, student_payload)

        resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        # Puede aceptarla o rechazarla
        assert resp.status_code in [200, 400]

    def test_group_code_case_insensitive(self, app_ctx):
        """POST /api/submissions/join - Código de grupo es case-insensitive"""
        client, modules = app_ctx
        teacher_payload = _lti_payload(user_id="teacher1", roles="Instructor", resource_link_id="act-case-001")
        _launch_lti(client, teacher_payload)

        # Crear actividad grupal
        activity_body = {
            "title": "Grupo",
            "description": "Test case",
            "activity_type": "group",
            "max_group_size": 3,
        }
        create_resp = client.post("/api/activities", json=activity_body)
        activity_id = create_resp.json()["activity"]["id"]

        # Líder crea grupo
        leader_payload = _lti_payload(user_id="student1", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, leader_payload)

        sub_resp = client.post(
            f"/api/activities/{activity_id}/submissions",
            files={"file": ("test.txt", b"Content", "text/plain")},
        )
        group_code = sub_resp.json()["submission"]["file_submission"]["group_code"]

        # Otro estudiante se une con código en minúsculas
        member_payload = _lti_payload(user_id="student2", roles="Learner", resource_link_id=activity_id)
        _launch_lti(client, member_payload)

        resp = client.post(
            "/api/submissions/join",
            json={"activity_id": activity_id, "group_code": group_code.lower()},
        )
        assert resp.status_code == 200
