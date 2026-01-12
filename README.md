# LAMBA - Learning Activities & Machine-Based Assessment

An LTI activity for submitting and evaluating educational assignments with automated feedback using LAMB <https://lamb-project.org>. It integrates with LMS platforms like <https://moodle.org> via LTI 1.1.

## Features

- 🎓 **Activity Management**: Create and manage individual or group activities
- 🤖 **Automated Assessment**: Integration with LAMB models for AI-powered evaluation
- 📝 **Student Submissions**: Individual or group submission system with shared codes
- 📊 **Grading**: Automatic grade submission to Moodle via LTI
- 🌐 **Multilingual**: Support for Catalan, Spanish, and English
- 🔒 **LTI Integration**: Authentication and authorization via LTI 1.1

## Requirements

- Python 3.8+
- Node.js 18+
- Moodle with LTI 1.1 support

## Installation

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file based on `env.example`:

```env
# LTI Configuration (REQUIRED)
OAUTH_CONSUMER_KEY=your_consumer_key
LTI_SECRET=your_secret

# Database Configuration (OPTIONAL)
DATABASE_URL=sqlite:///./lamba.db

# HTTPS Configuration for production (OPTIONAL)
HTTPS_ENABLED=false
ALLOWED_ORIGINS=*

# LAMB API Configuration (OPTIONAL)
LAMB_API_URL=http://lamb.lamb-project.org:9099
LAMB_BEARER_TOKEN=your_token
LAMB_TIMEOUT=30

# Administrator Credentials (OPTIONAL)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

**Note**: If you use `https_server.py`, the `HTTPS_ENABLED` and `ALLOWED_ORIGINS` variables are automatically configured for HTTPS. For production, change `ALLOWED_ORIGINS` to the specific allowed domains.

### 2. Frontend

```bash
cd frontend/svelte-app
npm install
npm run build
```

## Running the Application

### Option 1: HTTPS (Recommended for production and development with Moodle)

1. **Generate SSL certificates** (first time only):

```bash
cd backend
python generate_ssl_cert.py
```

This will create self-signed certificates in the `backend/ssl/` folder:

- `cert.pem` - SSL Certificate
- `key.pem` - Private Key

2. **Start the HTTPS server**:

```bash
python https_server.py
```

The application will be available at:

- `https://localhost:9099` (Local)
- `https://YOUR_IP:9099` (Local network/Tailscale)

**Important note**: When using self-signed certificates, your browser will display a security warning. Click "Advanced" and "Proceed to site" to continue. This is normal in development environments.

### Option 2: HTTP (For local development only)

```bash
cd backend
python -m uvicorn main:app --reload --port 9099
```

The application will be available at `http://localhost:9099`

**⚠️ Warning**: Moodle may require HTTPS for LTI integration in some environments.

## Moodle Configuration

### 1. Add LTI External Tool

1. Go to `Site administration` > `Plugins` > `Activities` > `External tool` > `Manage tools`
2. Click `Configure a tool manually`
3. Configure:
   - **Tool name**: LAMBA
   - **Tool URL**: `https://your-server:9099/lti` (or `https://localhost:9099/lti` for local development)
   - **LTI version**: LTI 1.0/1.1
   - **Consumer key**: The value of `OAUTH_CONSUMER_KEY` from your `.env`
   - **Shared secret**: The value of `LTI_SECRET` from your `.env`
   - **Default launch container**: New window
   - **⚠️ Important**: Use `https://` in the URL

4. Under **Privacy**:
   - ✅ Share launcher's name with tool: Always
   - ✅ Share launcher's email with tool: Always
   - ✅ Accept grades from the tool: Always

5. Under **Services**:
   - ✅ IMS LTI Assignment and Grade Services
   - ✅ IMS LTI Names and Role Provisioning
   - ✅ Tool Settings

### 2. Create Activities in Moodle

1. In your course, add a new activity of type **External tool**
2. Select **LAMBA** as the preconfigured tool
3. **Important**: The activity name in Moodle must match the activity title in LAMBA
4. Configure grading:
   - ✅ Allow LAMBA to add grades to the gradebook
   - **Grade type**: Point
   - **Maximum grade**: 10
   - **Grade to pass**: 5.00

## Project Structure

```
.
├── backend/
│   ├── main.py                   # Application entry point
│   ├── https_server.py           # HTTPS server for production
│   ├── generate_ssl_cert.py      # Script to generate SSL certificates
│   ├── config.py                 # Configuration and environment variables
│   ├── database.py               # Database configuration
│   ├── db_models.py              # Database models (SQLAlchemy)
│   ├── models.py                 # Pydantic models for API
│   ├── activities_router.py      # Activities endpoints
│   ├── activities_service.py     # Activities business logic
│   ├── admin_router.py           # Administration endpoints
│   ├── admin_service.py          # Administration service
│   ├── submissions_router.py     # Submissions endpoints
│   ├── grades_router.py          # Grades endpoints
│   ├── grade_service.py          # Grades service
│   ├── lti_service.py            # LTI service for grade submission
│   ├── lamb_api_service.py       # LAMB API integration
│   ├── storage_service.py        # Uploaded files management
│   ├── user_service.py           # Users business logic
│   ├── course_service.py         # Courses business logic
│   ├── moodle_service.py         # Moodle business logic
│   ├── document_extractor.py     # Document text extraction
│   ├── requirements.txt          # Python dependencies
│   ├── API_DOCUMENTATION.md      # Complete API documentation
│   └── ssl/                      # SSL certificates (generated)
│
└── frontend/svelte-app/
    ├── src/
    │   ├── routes/
    │   │   ├── +page.svelte                # Main page
    │   │   ├── +layout.svelte              # Root layout
    │   │   ├── +layout.js                  # Routes configuration
    │   │   ├── actividad/
    │   │   │   └── [activityId]/
    │   │   │       └── +page.svelte        # Specific activity view
    │   │   └── admin/
    │   │       ├── +page.svelte            # Admin login page
    │   │       ├── +layout.svelte          # Admin layout
    │   │       └── dashboard/
    │   │           ├── +page.svelte        # Admin main dashboard
    │   │           ├── activities/         # Activities management
    │   │           ├── users/              # Users management
    │   │           ├── submissions/        # Submissions management
    │   │           ├── grades/             # Grades management
    │   │           ├── courses/            # Courses management
    │   │           ├── files/              # Files management
    │   │           └── moodle/             # Moodle configuration
    │   ├── lib/
    │   │   ├── auth.js                     # LTI authentication
    │   │   ├── admin.js                    # Administration logic
    │   │   ├── components/
    │   │   │   ├── Nav.svelte              # Main navigation
    │   │   │   ├── AdminNav.svelte         # Admin navigation
    │   │   │   ├── ActivityForm.svelte     # Activities form
    │   │   │   ├── DataTable.svelte        # Reusable data table
    │   │   │   └── LanguageSelector.svelte # Language selector
    │   │   └── i18n/
    │   │       ├── index.js                # i18n configuration
    │   │       ├── formatters.js           # Data formatters
    │   │       └── locales/
    │   │           ├── ca.json             # Catalan
    │   │           ├── es.json             # Spanish
    │   │           └── en.json             # English
    │   ├── app.html                        # Root HTML
    │   ├── app.css                         # Global styles
    │   ├── app.d.ts                        # TypeScript types
    │   └── tests/                          # Tests
    ├── package.json
    ├── svelte.config.js                    # Svelte configuration
    ├── vite.config.js                      # Vite configuration
    ├── vitest.config.js                    # Vitest configuration
    ├── eslint.config.js                    # ESLint configuration
    ├── jsconfig.json                       # JavaScript configuration
    └── static/
        ├── config.js                       # Frontend configuration
        └── img/                            # Static images
```

## Usage

### For Administrators

1. Access LAMBA as administrator at `https://localhost:9099/admin`
2. Log in with the credentials configured in `.env`:
   - Username: `ADMIN_USERNAME`
   - Password: `ADMIN_PASSWORD`
3. In the administration panel you can:
   - **Manage activities**: View, create, edit, and delete activities
   - **Manage users**: View registered user information
   - **View submissions**: Monitor all student submissions
   - **Manage grades**: Review and send grades to Moodle
   - **Configure LAMB evaluators**: Associate AI evaluators with activities

### For Teachers

1. Access LAMBA from Moodle
2. Create a new activity specifying:
   - Title
   - Description
   - Type (individual or group)
   - Deadline (optional)
   - LAMB evaluator ID (optional, for automatic assessment)
3. Students will be able to view and submit the activity
4. Review submissions, evaluate (manually or automatically), and send grades to Moodle

### For Students

1. Access the activity from Moodle
2. Read the activity description
3. Upload your document (individual) or join a group with a shared code
4. Wait for the teacher's evaluation
5. Your grade will be automatically sent to Moodle

## Technologies Used

### Backend

- **FastAPI**: Modern and fast web framework
- **SQLAlchemy**: ORM for database management
- **SQLite**: Database (easily replaceable with PostgreSQL/MySQL)
- **Requests**: HTTP client for LAMB API communication
- **PyLTI**: LTI 1.1 implementation
- **Cryptography**: SSL certificate generation

### Frontend

- **SvelteKit**: Web application framework
- **Svelte 5**: Reactive UI library
- **Tailwind CSS**: Utility-first CSS framework
- **svelte-i18n**: Internationalization

## Troubleshooting

### SSL Certificates

**Problem**: The browser doesn't trust the self-signed certificate

**Solution**:

1. Click "Advanced" in the browser warning
2. Select "Proceed to localhost (unsafe)" or similar
3. For Chrome/Edge: type `thisisunsafe` when you see the warning (without any visible text field)

**Alternative**: Generate new certificates if the current ones have expired:

```bash
cd backend
python generate_ssl_cert.py
```

### Moodle Connection Error

**Problem**: Moodle cannot connect to LAMBA

**Solution**:

1. Verify that the URL in Moodle uses `https://` and the correct port (9099)
2. Make sure the firewall allows connections to port 9099
3. If using Tailscale or another VPN, use the virtual network IP
4. Verify that `OAUTH_CONSUMER_KEY` and `LTI_SECRET` match between Moodle and `.env`

### Automatic Assessment Not Working

**Problem**: Error when evaluating with LAMB

**Solution**:

1. Verify that `LAMB_API_URL` and `LAMB_BEARER_TOKEN` are correct in `.env`
2. Make sure the `evaluator_id` configured in the activity exists in LAMB
3. Verify that uploaded documents are PDF, DOCX, or TXT (supported formats)

### Grades Not Being Sent to Moodle

**Problem**: Error when synchronizing grades

**Solution**:

1. Verify that the activity in Moodle has the "Accept grades from the tool" option enabled
2. Make sure the maximum grade in Moodle is 10
3. Check that students accessed the activity from Moodle (required to obtain `lis_result_sourcedid`)

## Additional Documentation

- **API Documentation**: See `backend/API_DOCUMENTATION.md` for complete documentation of all endpoints
- **Swagger UI**: Available at `https://localhost:9099/docs` when the server is running
- **ReDoc**: Available at `https://localhost:9099/redoc` for an alternative API view

## License

LAMB is licensed under the GNU General Public License v3.0 (GPL v3).

Copyright (c) 2025-2026 Arnau Tajahuerce @ArnauTajahuerce, Marc Alier @granludo (UPC), Maria José Casañ (UPC), Juanan Pereira (UPV/EHU) @juananpe

See [LICENSE](https://github.com/Lamb-Project/lamb/blob/main/LICENSE) for full details.
