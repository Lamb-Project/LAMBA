# LAMBA - Technical Architecture Document

## Document Information

| Field | Value |
|-------|-------|
| **Project** | LAMBA - Learning Activities & Machine-Based Assessment |
| **Version** | 1.0.0 |
| **Last Updated** | January 2026 |
| **Architecture Style** | Monolithic with service layers |

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

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
│  │  │  │Activities│  │   User   │  │  Course  │  │  Moodle  │        │ │   │
│  │  │  │ Service  │  │ Service  │  │ Service  │  │ Service  │        │ │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │ │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │   │
│  │  │  │  Grade   │  │   LTI    │  │  Storage │  │ LAMB API │        │ │   │
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

### 1.2 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | SvelteKit 2.x + Svelte 5 | Reactive UI framework |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **i18n** | svelte-i18n | Internationalization |
| **Backend** | FastAPI (Python 3.8+) | REST API server |
| **ORM** | SQLAlchemy | Database abstraction |
| **Database** | SQLite | Persistent storage |
| **Build Tools** | Vite | Frontend bundling |
| **Testing** | Vitest, pytest | Test frameworks |

---

## 2. System Components

### 2.1 Backend Architecture

#### 2.1.1 Application Entry Point (`main.py`)

```python
# Core responsibilities:
# - FastAPI application initialization
# - Router registration
# - CORS middleware configuration
# - LTI session management
# - Static file serving (SPA)

app = FastAPI(
    title="LAMBA",
    description="Learning Activities & Machine-Based Assessment",
    version="1.0.0",
    lifespan=lifespan  # Database initialization
)

# Routers mounted at:
# /api/activities - Activity CRUD operations
# /api/submissions - Submission management
# /api/grades - Grade operations
# /api/admin/* - Administration endpoints
# /lti - LTI launch endpoint
# /api/lti-data - Session data retrieval
```

#### 2.1.2 Router Layer

| Router | File | Prefix | Description |
|--------|------|--------|-------------|
| Activities | `activities_router.py` | `/api/activities` | CRUD for activities, submissions, evaluation |
| Submissions | `submissions_router.py` | `/api/submissions` | Student submission operations |
| Grades | `grades_router.py` | `/api/grades` | Grade management |
| Admin | `admin_router.py` | `/api/admin` | Administration operations |

#### 2.1.3 Service Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ActivitiesService                                              │
│  ├── create_activity()           Create new activity            │
│  ├── create_submission()         Handle file uploads            │
│  ├── submit_with_group_code()    Join existing group            │
│  ├── get_student_submission()    Retrieve student's work        │
│  ├── get_submissions_by_activity() List all submissions         │
│  └── update_activity()           Modify activity settings       │
│                                                                  │
│  GradeService                                                   │
│  ├── create_or_update_grade()    Save/update grade              │
│  ├── get_grade_by_file_submission() Retrieve grade              │
│  └── evaluate_submission()       Trigger AI evaluation          │
│                                                                  │
│  LTIGradeService                                                │
│  ├── send_grade_to_moodle()      Single grade passback          │
│  └── send_activity_grades_to_moodle() Batch grade sync          │
│                                                                  │
│  LAMBAPIService                                                 │
│  ├── verify_model_exists()       Check evaluator availability   │
│  ├── evaluate_text()             Call LAMB /chat/completions    │
│  └── parse_evaluation_response() Extract score from response    │
│                                                                  │
│  FileStorageService                                             │
│  ├── save_submission_file()      Persist uploaded file          │
│  ├── ensure_activity_directory() Create folder structure        │
│  └── sanitize_filename()         Safe filename generation       │
│                                                                  │
│  UserService / CourseService / MoodleService                    │
│  └── create_or_update_*()        Entity management              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Layer

#### 2.2.1 Database Schema (ERD)

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
                              │ PK id (varchar)     │
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
│ FK student_id           │           │    score (float)        │ ◄── 0-10
│ FK student_moodle_id    │           │    comment (text)       │
│    activity_id          │           │    created_at           │
│    activity_moodle_id   │           └─────────────────────────┘
│    lis_result_sourcedid │ ◄── For grade passback
│    joined_at            │
│    sent_to_moodle       │ ◄── Boolean flag
│    sent_to_moodle_at    │
└─────────────────────────┘
```

#### 2.2.2 Multi-Tenancy Model

LAMBA uses **composite primary keys** to ensure complete isolation between Moodle instances:

```python
# Example: ActivityDB composite key
class ActivityDB(Base):
    id = Column(String, primary_key=True)           # Activity ID (resource_link_id)
    course_moodle_id = Column(String, primary_key=True)  # Moodle instance ID
    
# This ensures Activity ID "123" from Moodle A is different from 
# Activity ID "123" from Moodle B
```

### 2.3 Frontend Architecture

#### 2.3.1 Route Structure

```
frontend/svelte-app/src/routes/
├── +page.svelte              # Main page (role-based: create activity / submit)
├── +layout.svelte            # Root layout with language selector
├── +error.svelte             # Error boundary
├── actividad/
│   └── [activityId]/
│       └── +page.svelte      # Activity detail (teacher: submissions list)
└── admin/
    ├── +page.svelte          # Admin login
    ├── +layout.svelte        # Admin layout with sidebar
    └── dashboard/
        ├── +page.svelte      # Dashboard overview
        ├── activities/       # Activity management
        ├── users/            # User management
        ├── submissions/      # Submission management
        ├── grades/           # Grade management
        ├── courses/          # Course management
        ├── files/            # File management
        └── moodle/           # Moodle instances
```

#### 2.3.2 Component Architecture

```
lib/
├── auth.js                   # LTI authentication utilities
│   ├── fetchLTIData()       # Get current session data
│   ├── isStudentRole()      # Role checking
│   └── isTeacherOrAdminRole()
│
├── admin.js                  # Admin API client
│   ├── login()
│   ├── logout()
│   └── checkSession()
│
├── components/
│   ├── Nav.svelte           # Main navigation bar
│   ├── AdminNav.svelte      # Admin sidebar navigation
│   ├── ActivityForm.svelte  # Activity creation form
│   ├── DataTable.svelte     # Reusable data table
│   └── LanguageSelector.svelte
│
└── i18n/
    ├── index.js             # i18n configuration
    ├── formatters.js        # Date/size formatters
    └── locales/
        ├── ca.json          # Catalan translations
        ├── es.json          # Spanish translations
        └── en.json          # English translations
```

#### 2.3.3 State Management

LAMBA uses Svelte 5's native reactivity with `$state` runes:

```svelte
<script>
  // Reactive state declarations
  let userRole = $state(null);
  let loading = $state(true);
  let error = $state(null);
  
  // Derived computations
  let isTeacher = $derived(userRole === 'teacher');
</script>
```

---

## 3. Key Workflows

### 3.1 LTI Launch Sequence

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ Moodle │     │ LAMBA  │     │ Session│     │  DB    │
│  LMS   │     │ Server │     │ Store  │     │        │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │
    │ POST /lti    │              │              │
    │ (LTI params) │              │              │
    │─────────────►│              │              │
    │              │              │              │
    │              │ Generate session_id         │
    │              │──────────────►│              │
    │              │              │              │
    │              │ Create/Update Moodle instance
    │              │─────────────────────────────►│
    │              │              │              │
    │              │ Create/Update User          │
    │              │─────────────────────────────►│
    │              │              │              │
    │              │ Create/Update Course        │
    │              │─────────────────────────────►│
    │              │              │              │
    │  303 Redirect│              │              │
    │  + Set Cookie│              │              │
    │◄─────────────│              │              │
    │              │              │              │
```

**Session ID Generation**:
```python
session_id = hashlib.md5(
    f"{user_id}_{context_id}_{resource_link_id}".encode()
).hexdigest()
```

### 3.2 Submission & Evaluation Flow

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│Student │     │Frontend│     │ Backend│     │ Storage│     │ LAMB   │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │              │
    │ Select file  │              │              │              │
    │─────────────►│              │              │              │
    │              │              │              │              │
    │              │ POST /api/activities/{id}/submissions      │
    │              │─────────────►│              │              │
    │              │              │              │              │
    │              │              │ Save file   │              │
    │              │              │─────────────►│              │
    │              │              │              │              │
    │              │              │ Create FileSubmission       │
    │              │              │ Create StudentSubmission    │
    │              │              │              │              │
    │              │  Success     │              │              │
    │◄─────────────│◄─────────────│              │              │
    │              │              │              │              │

    ═══════════════════════════════════════════════════════════════
    │ TEACHER TRIGGERS EVALUATION                                  │
    ═══════════════════════════════════════════════════════════════

┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│Teacher │     │Frontend│     │ Backend│     │Doc Ext.│     │ LAMB   │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │              │
    │ Click Evaluate              │              │              │
    │─────────────►│              │              │              │
    │              │              │              │              │
    │              │ POST /api/activities/{id}/evaluate         │
    │              │─────────────►│              │              │
    │              │              │              │              │
    │              │              │ For each submission:        │
    │              │              │──────────────►│              │
    │              │              │ Extract text │              │
    │              │              │◄──────────────│              │
    │              │              │              │              │
    │              │              │ POST /chat/completions      │
    │              │              │─────────────────────────────►│
    │              │              │              │              │
    │              │              │    Score + Feedback         │
    │              │              │◄─────────────────────────────│
    │              │              │              │              │
    │              │              │ Parse "NOTA FINAL: X.X"     │
    │              │              │ Create Grade │              │
    │              │              │              │              │
    │              │ {grades_created: N}         │              │
    │◄─────────────│◄─────────────│              │              │
```

### 3.3 Grade Passback to Moodle

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│Teacher │     │ LAMBA  │     │ LTI    │     │ Moodle │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │
    │ Click Sync   │              │              │
    │─────────────►│              │              │
    │              │              │              │
    │              │ For each graded submission: │
    │              │              │              │
    │              │ Build XML    │              │
    │              │─────────────►│              │
    │              │              │              │
    │              │ Sign with OAuth 1.0a       │
    │              │─────────────►│              │
    │              │              │              │
    │              │              │ POST replaceResult
    │              │              │─────────────►│
    │              │              │              │
    │              │              │   Success   │
    │              │              │◄─────────────│
    │              │              │              │
    │              │ Mark sent_to_moodle = true │
    │              │              │              │
    │  Summary     │              │              │
    │◄─────────────│              │              │
```

**OAuth Signature Generation**:
```python
# 1. Normalize URL
normalized_url = scheme://host:port/path (no query)

# 2. Sort and encode parameters
params = oauth_consumer_key, oauth_nonce, oauth_signature_method,
         oauth_timestamp, oauth_version, oauth_body_hash

# 3. Build base string
base_string = "POST&{url}&{params}"

# 4. Sign with HMAC-SHA1
signature = HMAC-SHA1(consumer_secret + "&", base_string)
```

---

## 4. API Design

### 4.1 RESTful Endpoint Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/lti` | None | LTI launch entry point |
| `GET` | `/api/lti-data` | LTI Cookie | Get session data |
| `POST` | `/api/activities` | LTI (Teacher) | Create activity |
| `GET` | `/api/activities/{id}` | LTI (Teacher) | Get activity |
| `PUT` | `/api/activities/{id}` | LTI (Teacher) | Update activity |
| `GET` | `/api/activities/{id}/view` | LTI (Student) | Student activity view |
| `GET` | `/api/activities/{id}/submissions` | LTI (Teacher) | List submissions |
| `POST` | `/api/activities/{id}/submissions` | LTI (Student) | Submit file |
| `POST` | `/api/activities/{id}/evaluate` | LTI (Teacher) | Trigger AI evaluation |
| `POST` | `/api/activities/{id}/grades/sync` | LTI (Teacher) | Sync grades to Moodle |
| `GET` | `/api/submissions/me` | LTI (Student) | Get own submission |
| `POST` | `/api/submissions/join` | LTI (Student) | Join group with code |
| `GET` | `/api/submissions/{id}/members` | LTI | Get group members |
| `POST` | `/api/grades/{submission_id}` | LTI (Teacher) | Create/update grade |
| `GET` | `/api/downloads/{path}` | LTI (Teacher) | Download file |
| `POST` | `/api/admin/login` | Credentials | Admin login |
| `POST` | `/api/admin/logout` | Admin Cookie | Admin logout |
| `GET` | `/api/admin/statistics` | Admin Cookie | Dashboard stats |
| `GET` | `/api/admin/*` | Admin Cookie | Entity listings |

### 4.2 Authentication Mechanisms

#### LTI Session (Students & Teachers)
```python
# Cookie-based session
@app.post("/lti")
async def process_lti_launch(request: Request):
    # ... validate LTI params ...
    response.set_cookie(
        key="lti_session",
        value=session_id,
        httponly=True,
        secure=is_https,
        samesite="lax",
        max_age=3600  # 1 hour
    )
```

#### Admin Session
```python
@router.post("/api/admin/login")
async def admin_login(credentials, response):
    # Validate against ADMIN_USERNAME/ADMIN_PASSWORD
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        secure=is_https,
        max_age=86400  # 24 hours
    )
```

### 4.3 Response Format Standards

**Success Response**:
```json
{
  "success": true,
  "message": "Operation completed",
  "data": { ... }
}
```

**Error Response**:
```json
{
  "detail": "Error description"
}
```

**List Response**:
```json
{
  "success": true,
  "data": [ ... ],
  "count": 42
}
```

---

## 5. Security Considerations

### 5.1 Authentication & Authorization

| Mechanism | Implementation |
|-----------|----------------|
| LTI OAuth | HMAC-SHA1 signature validation (planned) |
| Session cookies | HTTP-only, Secure (HTTPS), SameSite=Lax |
| Admin auth | Password-protected, environment variables |
| Role enforcement | Checked at router/service level |

### 5.2 Data Protection

| Concern | Mitigation |
|---------|------------|
| SQL Injection | SQLAlchemy ORM with parameterized queries |
| Path Traversal | `FileStorageService.is_within_uploads()` validation |
| XSS | Svelte's automatic HTML escaping |
| CSRF | SameSite cookies, same-origin requests |
| Secrets in code | Environment variables for credentials |

### 5.3 File Upload Security

```python
# Validation checklist:
# 1. Size limit: 50MB max
# 2. Path sanitization
# 3. Filename sanitization
# 4. Storage outside web root
# 5. Access control via API (not direct)
```

---

## 6. Deployment Architecture

### 6.1 Single-Server Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Server                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              HTTPS Server (https_server.py)           │   │
│  │                    Port 9099                          │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │              FastAPI Application               │  │   │
│  │  │                                                │  │   │
│  │  │  ┌────────────────┐  ┌────────────────────┐   │  │   │
│  │  │  │   API Routes   │  │   Static Files     │   │  │   │
│  │  │  │   /api/*       │  │   /app/* (SvelteKit│   │  │   │
│  │  │  │   /lti         │  │   build)           │   │  │   │
│  │  │  └────────────────┘  └────────────────────┘   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │     SQLite DB        │  │     uploads/             │     │
│  │     lamba.db         │  │     (file storage)       │     │
│  └──────────────────────┘  └──────────────────────────┘     │
│                                                              │
│  ┌──────────────────────┐                                   │
│  │    ssl/              │                                   │
│  │    cert.pem, key.pem │                                   │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Environment Configuration

**Required Variables**:
```env
# LTI Configuration
OAUTH_CONSUMER_KEY=your_consumer_key
LTI_SECRET=your_secret

# Database
DATABASE_URL=sqlite:///./lamba.db

# LAMB Integration
LAMB_API_URL=http://lamb.lamb-project.org:9099
LAMB_BEARER_TOKEN=your_token
LAMB_TIMEOUT=30

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password

# Optional
HTTPS_ENABLED=true
ALLOWED_ORIGINS=https://your-moodle.edu
```

### 6.3 Build Process

```bash
# Backend (production)
cd backend
pip install -r requirements.txt
python generate_ssl_cert.py  # First time only
python https_server.py

# Frontend (build for production)
cd frontend/svelte-app
npm install
npm run build
# Output: frontend/build/ → served by backend
```

---

## 7. Scalability Considerations

### 7.1 Current Limitations

| Component | Limitation | Impact |
|-----------|------------|--------|
| SQLite | Single-writer, file-based | ~100 concurrent users |
| In-memory sessions | Lost on restart | Requires re-login |
| Single-process | No horizontal scaling | Bounded by server capacity |
| Synchronous LAMB calls | Blocking during evaluation | Slow batch operations |

### 7.2 Future Scaling Path

```
Phase 1 (Current)           Phase 2 (Medium-term)       Phase 3 (Long-term)
─────────────────           ─────────────────────       ─────────────────────
Single Server               Multi-Process               Distributed
SQLite                      PostgreSQL                  PostgreSQL + Redis
In-memory sessions          Redis sessions              Redis Cluster
Sync LAMB calls             Async + Celery              Message Queue (RabbitMQ)
```

---

## 8. Monitoring & Observability

### 8.1 Logging Strategy

```python
# Current: Python logging module
logging.basicConfig(level=logging.INFO)

# Log categories:
# - LTI launch events
# - Authentication events
# - LAMB API interactions
# - Grade passback results
# - Error conditions
```

### 8.2 Health Indicators

| Endpoint | Check |
|----------|-------|
| `/docs` | FastAPI operational |
| `/api/admin/check-session` | Backend + DB |
| Moodle LTI launch | Full integration |

---

## 9. Testing Strategy

### 9.1 Test Types

| Type | Framework | Location | Coverage |
|------|-----------|----------|----------|
| Unit (Backend) | pytest | `backend/tests/` | Services, utilities |
| Unit (Frontend) | Vitest | `frontend/svelte-app/src/tests/lib/` | Utilities, formatters |
| Integration | Vitest | `frontend/svelte-app/src/tests/integration/` | API client tests |
| Functional | pytest | `backend/tests/test_functional.py` | End-to-end workflows |

### 9.2 Running Tests

```bash
# Backend
cd backend
pytest tests/

# Frontend
cd frontend/svelte-app
npm run test
```

---

## 10. Code Organization Patterns

### 10.1 Service Layer Pattern

```python
# Each service encapsulates business logic for a domain
class ActivitiesService:
    @staticmethod
    def create_activity(...) -> Activity:
        # Validation
        # Database operations
        # Return domain model
        
    @staticmethod
    def create_submission(...) -> OptimizedSubmissionView:
        # File handling
        # Database operations
        # Group logic
```

### 10.2 Router Pattern

```python
# Routers handle HTTP concerns, delegate to services
@router.post("/")
async def create_activity(activity_data: ActivityCreate, request: Request):
    # Extract session data
    # Validate permissions
    # Call service
    # Format response
```

### 10.3 Model Separation

```python
# DB Models (db_models.py) - SQLAlchemy
class ActivityDB(Base):
    __tablename__ = "activities"
    # Database-specific fields and relationships

# API Models (models.py) - Pydantic
class Activity(BaseModel):
    # Serialization, validation, API contracts
```

---

## 11. Extension Points

### 11.1 Adding New LMS Support

1. Create new authentication handler
2. Implement grade passback protocol (LTI 1.3, etc.)
3. Add LMS-specific user provisioning

### 11.2 Adding New File Types

1. Extend `document_extractor.py`
2. Add extraction logic for new MIME types
3. Update frontend file input accept list

### 11.3 Adding New Evaluation Providers

1. Create new service similar to `LAMBAPIService`
2. Implement `evaluate_text()` interface
3. Add configuration for provider selection

---

## 12. Related Documentation

- [PRD](./prd.md) - Product Requirements Document
- [API Documentation](../backend/API_DOCUMENTATION.md) - Full API reference
- [LAMB Architecture](./lamb-project-docs/lamb_architecture_nano.md) - LAMB platform context
- [README](../README.md) - Quick start guide
