# LAMBA - Technical Architecture Document

## Document Information

| Field | Value |
|-------|-------|
| **Project** | LAMBA - Learning Activities & Machine-Based Assessment |
| **Version** | 1.2.0 |
| **Last Updated** | January 25, 2026 |
| **Architecture Style** | Monolithic with service layers |

---

## 1. Project Overview

### 1.1 What is LAMBA?

LAMBA is an **LTI 1.1 Tool Provider** that integrates with Moodle (or any LMS supporting LTI) to provide:
- **Activity creation** for teachers (individual or group assignments)
- **File submission** for students
- **AI-powered automatic evaluation** using the LAMB platform
- **Grade passback** to the LMS via LTI Outcome Service

### 1.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MOODLE LMS                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │   Course 1   │  │   Course 2   │  │   Course N   │                       │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │                       │
│  │  │LTI Tool│  │  │  │LTI Tool│  │  │  │LTI Tool│  │                       │
│  │  └───┬────┘  │  │  └───┬────┘  │  │  └───┬────┘  │                       │
│  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘                       │
│         │                 │                 │                                │
└─────────┼─────────────────┼─────────────────┼────────────────────────────────┘
          │ LTI 1.1         │                 │
          │ Launch          │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LAMBA APPLICATION                                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        FRONTEND (SvelteKit)                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │ Student  │  │ Teacher  │  │  Admin   │  │  Shared  │              │   │
│  │  │  Views   │  │  Views   │  │  Views   │  │Components│              │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ REST API                                │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        BACKEND (FastAPI)                              │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │   LTI   │  │Activity │  │Submission│ │  Grade  │  │  Admin  │    │   │
│  │  │ Router  │  │ Router  │  │ Router   │ │ Router  │  │ Router  │    │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │   │
│  │       │            │            │            │            │          │   │
│  │       └────────────┴────────────┴────────────┴────────────┘          │   │
│  │                                 │                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │                       SERVICE LAYER                              │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │   │
│  │  │  │Activities│  │Evaluation│  │  Grade   │  │  LAMB API│        │ │   │
│  │  │  │ Service  │  │ Service  │  │ Service  │  │ Service  │        │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘        │ │   │
│  │  └──────────────────────────────────────────────────┼──────────────┘ │   │
│  └─────────────────────────────────────────────────────┼────────────────┘   │
│                                                        │                     │
│  ┌─────────────────────────┐                          │                     │
│  │      DATA LAYER         │                          │                     │
│  │  ┌───────────────────┐  │                          │                     │
│  │  │    SQLite DB      │  │                          │                     │
│  │  │  (SQLAlchemy ORM) │  │                          │                     │
│  │  └───────────────────┘  │                          │                     │
│  │  ┌───────────────────┐  │                          │                     │
│  │  │   File Storage    │  │                          │                     │
│  │  │ (uploads folder)  │  │                          │                     │
│  │  └───────────────────┘  │                          │                     │
│  └─────────────────────────┘                          │                     │
└───────────────────────────────────────────────────────┼─────────────────────┘
                                                        │
                                                        │ HTTP/REST
                                                        ▼
                                  ┌─────────────────────────────────────────┐
                                  │            LAMB PLATFORM                 │
                                  │  ┌─────────────────────────────────────┐ │
                                  │  │     AI Evaluation Service           │ │
                                  │  │  /v1/models  /chat/completions      │ │
                                  │  └─────────────────────────────────────┘ │
                                  └─────────────────────────────────────────┘
```

### 1.3 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | SvelteKit 2.x + Svelte 5 | Reactive UI framework with `$state` runes |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **i18n** | svelte-i18n | Internationalization (EN, ES, CA, EU) |
| **Backend** | FastAPI (Python 3.8+) | REST API server |
| **ORM** | SQLAlchemy | Database abstraction |
| **Database** | SQLite | Persistent storage |
| **Build Tools** | Vite | Frontend bundling |
| **Testing** | Vitest, pytest | Test frameworks |

---

## 2. Directory Structure

```
/opt/LAMBA/
├── backend/
│   ├── main.py                 # FastAPI app entry point, LTI endpoints
│   ├── config.py               # Environment variable loading
│   ├── database.py             # SQLAlchemy engine and session
│   ├── db_models.py            # SQLAlchemy ORM models
│   ├── models.py               # Pydantic API models
│   │
│   ├── activities_router.py    # Activity CRUD, submissions, evaluation endpoints
│   ├── activities_service.py   # Activity business logic
│   ├── submissions_router.py   # Student submission endpoints
│   ├── grades_router.py        # Grade management endpoints
│   ├── grade_service.py        # Grade business logic
│   ├── admin_router.py         # Admin dashboard endpoints
│   ├── admin_service.py        # Admin business logic
│   │
│   ├── evaluation_service.py   # Background AI evaluation management
│   ├── lamb_api_service.py     # LAMB API client (AI evaluation)
│   ├── lti_service.py          # LTI grade passback (OAuth 1.0a)
│   │
│   ├── document_extractor.py   # Text extraction (PDF, DOCX, TXT)
│   ├── storage_service.py      # File storage management
│   ├── user_service.py         # User CRUD
│   ├── course_service.py       # Course CRUD
│   ├── moodle_service.py       # Moodle instance CRUD
│   │
│   ├── uploads/                # Student file submissions
│   ├── lamba.db                # SQLite database
│   ├── requirements.txt        # Python dependencies
│   └── .env                    # Environment configuration
│
├── frontend/
│   └── svelte-app/
│       ├── src/
│       │   ├── routes/
│       │   │   ├── +page.svelte          # Main page (role-based)
│       │   │   ├── +layout.svelte        # Root layout
│       │   │   ├── actividad/
│       │   │   │   └── [activityId]/
│       │   │   │       └── +page.svelte  # Teacher: submissions view
│       │   │   └── admin/
│       │   │       └── dashboard/        # Admin panel pages
│       │   │
│       │   └── lib/
│       │       ├── auth.js               # LTI session management
│       │       ├── admin.js              # Admin API client
│       │       ├── components/           # Reusable components
│       │       └── i18n/                 # Internationalization
│       │           └── locales/          # Translation files (en, es, ca, eu)
│       │
│       └── static/                       # Static assets
│
└── Documentation/
    ├── lamba_architecture.md             # This file
    ├── prd.md                            # Product Requirements
    └── lamb-project-docs/                # LAMB platform docs
```

---

## 3. Database Schema

### 3.1 Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│   moodle_instances  │       │       users         │
├─────────────────────┤       ├─────────────────────┤
│ PK id (varchar)     │──┐    │ PK id (varchar)     │
│    name (varchar)   │  │    │ PK moodle_id (FK)   │──┐
│    lis_outcome_url  │  │    │    full_name        │  │
│    created_at       │  │    │    email            │  │
└─────────────────────┘  │    │    role             │  │
                         │    │    created_at       │  │
                         │    └─────────────────────┘  │
                         │                             │
                         │    ┌─────────────────────┐  │
                         └───►│      courses        │  │
                              ├─────────────────────┤  │
                              │ PK id (varchar)     │  │
                              │ PK moodle_id (FK)   │◄─┘
                              │    title (varchar)  │
                              │    created_at       │
                              └─────────┬───────────┘
                                        │
                                        │ 1:N
                                        ▼
                              ┌─────────────────────┐
                              │     activities      │
                              ├─────────────────────┤
                              │ PK id (varchar)     │ ◄── resource_link_id from LTI
                              │ PK course_moodle_id │
                              │    title            │
                              │    description      │
                              │    activity_type    │ ◄── "individual" | "group"
                              │    max_group_size   │
                              │ FK creator_id       │
                              │ FK creator_moodle_id│
                              │ FK course_id        │
                              │    deadline         │
                              │    evaluator_id     │ ◄── LAMB model reference
                              │    created_at       │
                              └─────────┬───────────┘
                                        │
                                        │ 1:N
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                       file_submissions                           │
├─────────────────────────────────────────────────────────────────┤
│ PK id (varchar)                                                  │
│    activity_id                                                   │
│    activity_moodle_id                                           │
│    file_name                                                     │
│    file_path              ◄── Relative path in uploads/         │
│    file_size                                                     │
│    file_type              ◄── MIME type                         │
│    uploaded_at                                                   │
│ FK uploaded_by                                                   │
│ FK uploaded_by_moodle_id                                        │
│    group_code             ◄── 8-char code for groups            │
│    max_group_members                                             │
│    evaluation_status      ◄── null/pending/processing/completed/error │
│    evaluation_started_at  ◄── For timeout detection             │
│    evaluation_error       ◄── Error message if failed           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            │ 1:N               │ 1:1               │
            ▼                   │                   ▼
┌─────────────────────────┐     │     ┌─────────────────────────┐
│  student_submissions    │     │     │        grades           │
├─────────────────────────┤     │     ├─────────────────────────┤
│ PK id (varchar)         │     │     │ PK id (varchar)         │
│ FK file_submission_id   │◄────┘     │ FK file_submission_id   │
│ FK student_id           │           │    ai_score (float?)    │ ◄── AI proposed (0-10)
│ FK student_moodle_id    │           │    ai_comment (text?)   │ ◄── AI feedback
│    activity_id          │           │    ai_evaluated_at      │
│    activity_moodle_id   │           │    score (float?)       │ ◄── Final grade (0-10)
│    lis_result_sourcedid │ ◄── For   │    comment (text?)      │ ◄── Professor feedback
│    joined_at            │   grade   │    created_at           │
│    sent_to_moodle       │   pass-   │    updated_at           │
│    sent_to_moodle_at    │   back    └─────────────────────────┘
└─────────────────────────┘
```

### 3.2 Multi-Tenancy Model

LAMBA uses **composite primary keys** to ensure complete isolation between Moodle instances:

```python
# Example: ActivityDB composite key
class ActivityDB(Base):
    id = Column(String, primary_key=True)           # Activity ID (resource_link_id)
    course_moodle_id = Column(String, primary_key=True)  # Moodle instance ID
    
# This ensures Activity ID "123" from Moodle A is different from 
# Activity ID "123" from Moodle B
```

**Key relationships:**
- All entities reference `moodle_id` as part of their composite key
- `activity.id` = LTI `resource_link_id` (unique per Moodle instance)
- `course.id` = LTI `context_id` (unique per Moodle instance)
- `user.id` = LTI `user_id` (unique per Moodle instance)

---

## 4. API Reference

### 4.1 LTI Endpoints (main.py)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/lti` | None | LTI launch entry point |
| `GET` | `/api/lti-data` | LTI Cookie/Header | Get session data |
| `GET` | `/api/debug-mode` | LTI Cookie | Check if debug mode enabled |
| `GET` | `/api/downloads/{path}` | LTI (Teacher) | Download submission file |

### 4.2 Activities Router (`/api/activities`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/` | LTI (Teacher) | Create activity |
| `GET` | `/{id}` | LTI (Teacher) | Get activity |
| `PUT` | `/{id}` | LTI (Teacher) | Update activity |
| `GET` | `/{id}/view` | LTI (Student) | Student activity view |
| `GET` | `/{id}/submissions` | LTI (Teacher) | List all submissions |
| `POST` | `/{id}/submissions` | LTI (Student) | Submit file |
| `POST` | `/{id}/evaluate` | LTI (Teacher) | Start AI evaluation (background) |
| `GET` | `/{id}/evaluation-status` | LTI (Teacher) | Poll evaluation progress |
| `POST` | `/{id}/grades/sync` | LTI (Teacher) | Sync grades to Moodle |

### 4.3 Submissions Router (`/api/submissions`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/me` | LTI (Student) | Get own submission |
| `POST` | `/join` | LTI (Student) | Join group with code |
| `GET` | `/{id}/members` | LTI | Get group members |

### 4.4 Grades Router (`/api/grades`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/{submission_id}` | LTI (Teacher) | Create/update final grade |
| `POST` | `/activity/{id}/accept-ai-grades` | LTI (Teacher) | Accept all AI grades as final |

### 4.5 Admin Router (`/api/admin`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/login` | Credentials | Admin login |
| `POST` | `/logout` | Admin Cookie | Admin logout |
| `GET` | `/check-session` | Admin Cookie | Verify session |
| `GET` | `/statistics` | Admin Cookie | Dashboard stats |
| `GET` | `/moodle-instances` | Admin Cookie | List Moodle instances |
| `GET` | `/courses` | Admin Cookie | List courses |
| `GET` | `/activities` | Admin Cookie | List activities |
| `GET` | `/users` | Admin Cookie | List users |
| `GET` | `/submissions` | Admin Cookie | List submissions |
| `GET` | `/files` | Admin Cookie | List files |
| `GET` | `/grades` | Admin Cookie | List grades |
| `GET` | `/debug/lamb` | Admin Cookie | LAMB API debug info |
| `POST` | `/debug/lamb/verify-model` | Admin Cookie | Verify LAMB model |

---

## 5. Service Layer Details

### 5.1 ActivitiesService (`activities_service.py`)

**Purpose:** Core business logic for activities and submissions.

**Key Methods:**
```python
class ActivitiesService:
    @staticmethod
    def create_activity(activity_data, user_id, course_id, course_moodle_id, activity_id) -> Activity
    
    @staticmethod
    def create_submission(activity_id, student_id, student_name, student_email, 
                         file_name, file_content, file_size, file_type, 
                         course_id, course_moodle_id, student_moodle_id, 
                         lis_result_sourcedid) -> OptimizedSubmissionView
    
    @staticmethod
    def submit_with_group_code(activity_id, group_code, student_id, ...) -> OptimizedSubmissionView
    
    @staticmethod
    def get_submissions_by_activity(activity_id, activity_moodle_id) -> Dict[str, Any]
    # Returns: {activity, activity_type, total_submissions, submissions/groups}
```

### 5.2 EvaluationService (`evaluation_service.py`)

**Purpose:** Manages background AI evaluation jobs.

**Key Methods:**
```python
class EvaluationService:
    @staticmethod
    def start_evaluation(activity_id, activity_moodle_id, file_submission_ids, evaluator_id) -> Dict
    # Marks submissions as 'pending', returns immediately
    
    @staticmethod
    def process_evaluation_batch(activity_id, activity_moodle_id, file_submission_ids, 
                                  evaluator_id, is_debug_mode) -> Dict
    # Runs in background thread, calls LAMB API for each submission
    
    @staticmethod
    def get_evaluation_status(activity_id, activity_moodle_id, file_submission_ids) -> Dict
    # Returns current status for polling
    
    @staticmethod
    def reset_stuck_evaluations(activity_id, activity_moodle_id) -> int
    # Resets evaluations stuck > 5 minutes
```

**Evaluation Status Flow:**
```
null → pending → processing → completed
                     ↓
                   error
```

### 5.3 LAMBAPIService (`lamb_api_service.py`)

**Purpose:** Client for the LAMB AI evaluation API.

**Key Methods:**
```python
class LAMBAPIService:
    LAMB_API_URL = os.getenv('LAMB_API_URL')
    LAMB_BEARER_TOKEN = os.getenv('LAMB_BEARER_TOKEN')
    LAMB_TIMEOUT = int(os.getenv('LAMB_TIMEOUT', '30'))
    
    @staticmethod
    def verify_model_exists(evaluator_id) -> Dict[str, Any]
    # Checks if lamb_assistant.{evaluator_id} exists
    
    @staticmethod
    def evaluate_text(text, evaluator_id, timeout) -> Dict[str, Any]
    # Calls /chat/completions with extracted text
    
    @staticmethod
    def parse_evaluation_response(response) -> Dict[str, Any]
    # Extracts score and feedback from AI response
    
    @staticmethod
    def _extract_score_and_feedback(content) -> Dict[str, Any]
    # Regex patterns to find score in various formats
```

**Score Extraction Patterns:**
The `_extract_score_and_feedback` method searches for grades in these formats (in order):
1. `NOTA FINAL: X.X` or `FINAL SCORE: X.X`
2. `Nota: X.X`, `## Nota: X.X`, `**Nota:** X.X` (Spanish with markdown)
3. `Score: X.X`, `Grade: X.X`, `Puntuación: X.X`, `Calificación: X.X`
4. `X.X/10` pattern at end of text (fallback)

### 5.4 GradeService (`grade_service.py`)

**Purpose:** Grade CRUD operations.

**Key Methods:**
```python
class GradeService:
    @staticmethod
    def create_or_update_grade(file_submission_id, score, comment) -> Grade
    # Updates final grade (score, comment)
    
    @staticmethod
    def get_grade_by_file_submission(file_submission_id) -> Optional[Grade]
```

### 5.5 LTIGradeService (`lti_service.py`)

**Purpose:** LTI 1.1 grade passback to Moodle.

**Key Methods:**
```python
class LTIGradeService:
    @staticmethod
    def send_grade_to_moodle(lis_result_sourcedid, lis_outcome_service_url,
                             oauth_consumer_key, oauth_consumer_secret,
                             score, comment) -> Dict[str, Any]
    # Sends single grade via OAuth 1.0a signed XML
    
    @staticmethod
    def send_activity_grades_to_moodle(activity_id, activity_moodle_id) -> Dict[str, Any]
    # Sends all graded submissions for an activity
```

**Grade Normalization:**
- Input: 0-10 scale (LAMBA internal)
- Output: 0-1 scale (LTI standard)
- Conversion: `normalized_score = score / 10.0`

---

## 6. AI Evaluation Workflow

### 6.1 Complete Flow Diagram

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│Teacher │     │Frontend│     │ Backend│     │Doc Ext.│     │ LAMB   │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │              │
    │ 1. Select submissions      │              │              │
    │    & click "Evaluate"      │              │              │
    │─────────────►│              │              │              │
    │              │              │              │              │
    │              │ 2. POST /api/activities/{id}/evaluate     │
    │              │    {file_submission_ids: [...]}           │
    │              │─────────────►│              │              │
    │              │              │              │              │
    │              │              │ 3. Mark submissions        │
    │              │              │    as 'pending'            │
    │              │              │              │              │
    │              │ 4. {success: true, queued: N}             │
    │              │◄─────────────│              │              │
    │              │              │              │              │
    │  5. Show modal              │ 6. Background thread       │
    │     Start polling           │    starts processing       │
    │◄─────────────│              │              │              │
    │              │              │              │              │
    │              │ 7. GET /evaluation-status  │              │
    │              │─────────────►│              │              │
    │              │ {overall_status, counts, submissions}     │
    │              │◄─────────────│              │              │
    │              │              │              │              │
    │              │              │──────────────►│              │
    │              │              │ 8. Extract text from file  │
    │              │              │◄──────────────│              │
    │              │              │              │              │
    │              │              │ 9. POST /chat/completions  │
    │              │              │─────────────────────────────►│
    │              │              │              │              │
    │              │              │    AI Response (rubric +   │
    │              │              │    NOTA FINAL: X.X)        │
    │              │              │◄─────────────────────────────│
    │              │              │              │              │
    │              │              │ 10. Parse response,        │
    │              │              │     extract score          │
    │              │              │              │              │
    │              │              │ 11. Save to grades table:  │
    │              │              │     ai_score, ai_comment   │
    │              │              │              │              │
    │              │              │ 12. Update file_submission:│
    │              │              │     evaluation_status =    │
    │              │              │     'completed'            │
    │              │              │              │              │
    │              │ 13. Poll detects completion               │
    │  14. Modal   │◄─────────────│              │              │
    │      shows   │              │              │              │
    │      results │              │              │              │
    │◄─────────────│              │              │              │
```

### 6.2 Dual Grading System

LAMBA implements a two-stage grading workflow:

| Stage | Fields | Description |
|-------|--------|-------------|
| **1. AI Evaluation** | `ai_score`, `ai_comment`, `ai_evaluated_at` | Proposed grade from LAMB |
| **2. Professor Review** | `score`, `comment` | Final grade for LMS |

**Teacher Options:**
- "Accept AI Grade" per submission → copies `ai_score` → `score`
- "Accept All AI Grades" button → bulk copy for all submissions
- Manually enter different score/comment
- Only `score` (final grade) is sent to Moodle

### 6.3 Evaluation Status Constants

```python
STATUS_PENDING = 'pending'      # Queued for processing
STATUS_PROCESSING = 'processing' # Currently being evaluated
STATUS_COMPLETED = 'completed'   # Successfully evaluated
STATUS_ERROR = 'error'          # Evaluation failed
EVALUATION_TIMEOUT_MINUTES = 5  # Stuck evaluations reset after 5 min
```

---

## 7. LTI Integration

### 7.1 LTI Launch Flow

```
1. User clicks LTI tool in Moodle
2. Moodle POSTs to /lti with signed parameters
3. LAMBA extracts LTI data:
   - user_id, lis_person_name_full, lis_person_contact_email_primary
   - context_id, context_title (course)
   - resource_link_id, resource_link_title (activity)
   - roles (learner/instructor)
   - lis_result_sourcedid (for grade passback)
   - tool_consumer_instance_guid (Moodle instance ID)
4. Create/update Moodle instance, User, Course in DB
5. Generate session_id = MD5(user_id + context_id + resource_link_id)
6. Store LTI data in lti_data_store[session_id]
7. Set lti_session cookie
8. Redirect to / (student) or /actividad/{id} (teacher)
```

### 7.2 Session Management

**Cookie-based (primary):**
```python
response.set_cookie(
    key="lti_session",
    value=session_id,
    httponly=True,
    secure=is_https,
    samesite="none" if is_https else "lax",  # For iframe compatibility
    max_age=3600
)
```

**Header-based (fallback for iframe issues):**
```javascript
// Frontend stores session in sessionStorage
sessionStorage.setItem('lti_session', sessionId);

// API calls include header
headers.set('X-LTI-Session', sessionId);
```

### 7.3 Role Checking

```python
def check_teacher_role(lti_data):
    roles = lti_data['roles'].lower()
    return any(role in roles for role in ['administrator', 'instructor', 'teacher', 'admin'])

def check_student_role(lti_data):
    roles = lti_data['roles'].lower()
    return 'learner' in roles or 'student' in roles
```

---

## 8. Environment Configuration

### 8.1 Required Variables

```env
# LTI Configuration (REQUIRED)
LTI_SECRET=your_secret
OAUTH_CONSUMER_KEY=your_key

# Must match Moodle's External Tool configuration
```

### 8.2 Optional Variables

```env
# Database (default: SQLite)
DATABASE_URL=sqlite:///./lamba.db

# HTTPS (for production)
HTTPS_ENABLED=true

# CORS
ALLOWED_ORIGINS=https://your-moodle.edu

# LAMB AI Evaluation
LAMB_API_URL=http://lamb.lamb-project.org:9099
LAMB_BEARER_TOKEN=your_token
LAMB_TIMEOUT=30

# Admin Dashboard
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password

# Debug Mode (shows raw AI responses to teachers)
DEBUG=false
```

---

## 9. Frontend Architecture

### 9.1 Route Structure

```
/                           → Main page (role-based view)
  - Student: Submit file or join group
  - Teacher: Create activity form

/actividad/[activityId]     → Activity detail
  - Teacher: View submissions, grade, evaluate

/admin                      → Admin login
/admin/dashboard            → Admin dashboard
/admin/dashboard/activities → Activity management
/admin/dashboard/users      → User management
/admin/dashboard/grades     → Grade management
...
```

### 9.2 State Management (Svelte 5 Runes)

```svelte
<script>
  // Reactive state
  let loading = $state(true);
  let submissionsData = $state(null);
  let error = $state(null);
  
  // Derived values
  let isTeacher = $derived(userRole === 'teacher');
  
  // Effects
  $effect(() => {
    if (activityId) loadSubmissions();
  });
</script>
```

### 9.3 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `Nav.svelte` | `lib/components/` | Main navigation |
| `AdminNav.svelte` | `lib/components/` | Admin sidebar |
| `ActivityForm.svelte` | `lib/components/` | Create activity form |
| `DataTable.svelte` | `lib/components/` | Reusable data table |
| `LanguageSelector.svelte` | `lib/components/` | i18n language picker |

### 9.4 Authentication (`lib/auth.js`)

```javascript
// Initialize from URL (after LTI redirect)
initLTISession();

// Get stored session
getLTISessionId();

// Fetch with LTI session
await ltiAwareFetch('/api/activities/123/submissions');

// Role checking
isStudentRole(roles);
isTeacherOrAdminRole(roles);
```

---

## 10. Document Extraction

### 10.1 Supported Formats

| Format | Library | Extensions |
|--------|---------|------------|
| PDF | pypdf | `.pdf` |
| Word | python-docx | `.docx`, `.doc` |
| Text | Built-in | `.txt`, `.md`, `.py`, `.java`, `.cpp`, `.c`, `.js`, `.html`, `.css`, `.json`, `.xml` |

### 10.2 Usage

```python
from document_extractor import DocumentExtractor

text = DocumentExtractor.extract_text_from_file(file_path)
preview = DocumentExtractor.get_text_preview(text, max_length=500)
```

---

## 11. File Storage Structure

```
backend/uploads/
└── {moodle_id}/
    └── {course_id}/
        └── {activity_id}/
            └── {submission_id}/
                └── {sanitized_filename}
```

**Security:**
- Files stored outside web root
- Access only via `/api/downloads/{path}` with teacher role
- Path traversal prevented by `FileStorageService.is_within_uploads()`

---

## 12. Common Patterns

### 12.1 Composite Key Queries

```python
# Always filter by both activity_id AND moodle_id
activity = db.query(ActivityDB).filter(
    ActivityDB.id == activity_id,
    ActivityDB.course_moodle_id == moodle_id
).first()
```

### 12.2 Error Handling

```python
@router.post("/{activity_id}/evaluate")
async def evaluate_activity(activity_id: str, request: Request):
    try:
        lti_data = get_lti_session_data(request)  # Raises 401/404
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores...")
        # ... business logic ...
    except HTTPException:
        raise  # Re-raise HTTP errors as-is
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno")
```

### 12.3 Background Task Pattern

```python
# Router starts background task
@router.post("/{activity_id}/evaluate")
async def evaluate_activity(activity_id: str, request: Request, background_tasks: BackgroundTasks):
    # Validate, mark as pending
    start_result = EvaluationService.start_evaluation(...)
    
    # Queue background work
    background_tasks.add_task(
        run_background_evaluation,
        activity_id=activity_id,
        file_submission_ids=start_result['queued_ids'],
        evaluator_id=evaluator_id
    )
    
    return {"success": True, "queued": start_result['queued']}
```

---

## 13. Debugging & Troubleshooting

### 13.1 Debug Mode

Enable in `.env`:
```env
DEBUG=true
```

When enabled, teachers see raw AI responses in the evaluation modal.

### 13.2 Admin Debug Endpoints

```bash
# Test LAMB connectivity
GET /api/admin/debug/lamb

# Verify specific model
POST /api/admin/debug/lamb/verify-model
{"evaluator_id": "your_evaluator"}
```

### 13.3 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Activity not found" | LTI session expired | Re-launch from Moodle |
| AI grade shows but no score | Score format not matched | Check LAMB response format |
| Grades not syncing to Moodle | Missing `lis_result_sourcedid` | Student must have launched via LTI |
| Cookies not working in iframe | SameSite policy | Use HTTPS + `SameSite=None` |

### 13.4 Score Extraction Debug

If AI evaluation completes but `ai_score` is NULL:

1. Check `ai_comment` in database - does it contain a score?
2. Check format matches patterns in `_extract_score_and_feedback`:
   - `NOTA FINAL: 8.5`
   - `## Nota: 8.5`
   - `Score: 8.5`
   - `8.5/10`

3. Add new pattern to `lamb_api_service.py` if needed.

---

## 14. Testing

### 14.1 Backend Tests

```bash
cd backend
pytest tests/
```

### 14.2 Frontend Tests

```bash
cd frontend/svelte-app
npm run test
```

### 14.3 Test Files

| File | Type | Coverage |
|------|------|----------|
| `backend/tests/test_endpoints.py` | Integration | API endpoints |
| `backend/tests/test_functional.py` | Functional | End-to-end flows |
| `frontend/.../tests/lib/auth.test.js` | Unit | Auth utilities |
| `frontend/.../tests/lib/formatters.test.js` | Unit | Formatters |
| `frontend/.../tests/integration/api.test.js` | Integration | API client |

---

## 15. Development Quick Reference

### 15.1 Start Development Servers

```bash
# Backend (with auto-reload)
cd backend
uv run -m uvicorn main:app --reload --port 9091

# Frontend (dev mode)
cd frontend/svelte-app
npm run dev
```

### 15.2 Build for Production

```bash
# Frontend
cd frontend/svelte-app
npm run build
# Output: frontend/build/ → served by backend

# Backend serves both API and static frontend
python https_server.py  # or main.py
```

### 15.3 Database Inspection

```bash
cd backend
sqlite3 lamba.db

# Useful queries
.tables
.schema grades
SELECT * FROM grades WHERE ai_score IS NOT NULL;
```

---

## 16. Related Documentation

- [PRD](./prd.md) - Product Requirements Document
- [API Documentation](../backend/API_DOCUMENTATION.md) - Full API reference
- [LAMB Architecture](./lamb-project-docs/lamb_architecture_nano.md) - LAMB platform context
- [README](../README.md) - Quick start guide
