from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import os
import logging
import hashlib

import config  # Load environment variables via load_dotenv()
from activities_router import router as activities_router
from submissions_router import router as submissions_router
from grades_router import router as grades_router
from admin_router import router as admin_router
from user_service import UserService
from course_service import CourseService
from moodle_service import MoodleService
from database import init_db, get_db_session
from db_models import FileSubmissionDB, StudentSubmissionDB, UserDB
from storage_service import FileStorageService

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize database using lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación"""
    # Startup
    logging.info("Inicializando base de datos...")
    init_db()
    logging.info("Base de datos inicializada correctamente")
    yield
    # Shutdown (si se necesita algo en el futuro)

# Create FastAPI app
app = FastAPI(
    title="LAMBA", 
    description="Learning Activities & Machine-Based Assessment", 
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(activities_router, prefix="/api/activities", tags=["activities"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(grades_router, prefix="/api/grades", tags=["grades"])
app.include_router(admin_router, tags=["admin"])

# CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Static files configuration
FRONTEND_BUILD_DIR = "../frontend/build"
frontend_build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), FRONTEND_BUILD_DIR))
frontend_index_html = os.path.join(frontend_build_path, 'index.html')

def setup_static_files():
    """Configura el servicio de archivos estáticos para el build de SvelteKit"""
    if not os.path.isdir(frontend_build_path):
        return
    
    app_dir = os.path.join(frontend_build_path, "app")
    if os.path.isdir(app_dir):
        app.mount("/app", StaticFiles(directory=app_dir), name="svelte_assets")
    
    img_dir = os.path.join(frontend_build_path, "img")
    if os.path.isdir(img_dir):
        app.mount("/img", StaticFiles(directory=img_dir), name="svelte_images")

@app.get("/favicon.png", include_in_schema=False)
async def get_favicon():
    """Sirve el favicon"""
    favicon_path = os.path.join(frontend_build_path, "favicon.png")
    if os.path.isfile(favicon_path):
        return FileResponse(favicon_path)
    raise HTTPException(status_code=404, detail="Favicon no encontrado")

@app.get("/config.js", include_in_schema=False)
async def get_config_js():
    """Sirve el archivo config.js para la app SvelteKit"""
    config_path = os.path.join(frontend_build_path, "config.js")
    if os.path.isfile(config_path):
        return FileResponse(config_path)
    raise HTTPException(status_code=404, detail="Archivo de configuración no encontrado")

# Setup static files
setup_static_files()

# Almacén temporal de datos LTI
lti_data_store = {}

# Rutas LTI
@app.post("/lti")
async def process_lti_launch(request: Request):
    """Procesa el lanzamiento LTI desde Moodle y almacena los datos"""
    try:
        form_data = await request.form()
        post_data = dict(form_data)
        
        logging.info("Lanzamiento LTI recibido")
        
        lis_result_sourcedid = post_data.get("lis_result_sourcedid", "")
        user_id = post_data.get("user_id", "")
        logging.info(f"LTI Launch - Usuario: {user_id}, LIS Result SourcedID: {lis_result_sourcedid if lis_result_sourcedid else 'NO PROPORCIONADO'}")
        
        # Extraer datos LTI
        lti_launch_data = {
            "lti_message_type": post_data.get("lti_message_type", ""),
            "lti_version": post_data.get("lti_version", ""),
            "resource_link_id": post_data.get("resource_link_id", ""),
            "resource_link_title": post_data.get("resource_link_title", ""),
            "context_id": post_data.get("context_id", ""),
            "context_title": post_data.get("context_title", ""),
            "context_label": post_data.get("context_label", ""),
            "user_id": post_data.get("user_id", ""),
            "ext_user_username": post_data.get("ext_user_username", ""),
            "lis_person_name_given": post_data.get("lis_person_name_given", ""),
            "lis_person_name_family": post_data.get("lis_person_name_family", ""),
            "lis_person_name_full": post_data.get("lis_person_name_full", ""),
            "lis_person_contact_email_primary": post_data.get("lis_person_contact_email_primary", ""),
            "lis_result_sourcedid": post_data.get("lis_result_sourcedid", ""),
            "lis_outcome_service_url": post_data.get("lis_outcome_service_url", ""),
            "roles": post_data.get("roles", ""),
            "tool_consumer_instance_guid": post_data.get("tool_consumer_instance_guid", ""),
            "tool_consumer_instance_name": post_data.get("tool_consumer_instance_name", ""),
            "launch_presentation_return_url": post_data.get("launch_presentation_return_url", ""),
            "oauth_consumer_key": post_data.get("oauth_consumer_key", ""),
            "custom_parameters": {k: v for k, v in post_data.items() if k.startswith("custom_")},
            "all_parameters": dict(post_data)
        }
        
        # Generar ID de sesión
        session_id = hashlib.md5(
            f"{lti_launch_data['user_id']}_{lti_launch_data['context_id']}_{lti_launch_data['resource_link_id']}".encode()
        ).hexdigest()
        
        lti_data_store[session_id] = lti_launch_data
        
        # Crear o actualizar instancia de Moodle en la base de datos
        moodle_instance_id = None
        try:
            tool_consumer_instance_guid = lti_launch_data.get('tool_consumer_instance_guid', '')
            tool_consumer_instance_name = lti_launch_data.get('tool_consumer_instance_name', '')
            lis_outcome_service_url = lti_launch_data.get('lis_outcome_service_url', '')
            
            if tool_consumer_instance_guid and tool_consumer_instance_name:
                moodle = MoodleService.create_or_update_moodle(
                    moodle_id=tool_consumer_instance_guid,
                    name=tool_consumer_instance_name,
                    lis_outcome_service_url=lis_outcome_service_url if lis_outcome_service_url else None
                )
                moodle_instance_id = moodle.id
                logging.info(f"Instancia Moodle creada/actualizada: {moodle.id} - {moodle.name}")
        except Exception as e:
            logging.error(f"Error creando/actualizando instancia Moodle: {str(e)}")
        
        # Crear o actualizar usuario en la base de datos
        try:
            if moodle_instance_id:
                user = UserService.create_or_update_user(
                    user_id=lti_launch_data.get('user_id', ''),
                    moodle_id=moodle_instance_id,
                    full_name=lti_launch_data.get('lis_person_name_full', '') or lti_launch_data.get('ext_user_username', ''),
                    email=lti_launch_data.get('lis_person_contact_email_primary'),
                    roles=lti_launch_data.get('roles', '')
                )
                logging.info(f"Usuario creado/actualizado: {user.id} - {user.full_name} ({user.role})")
        except Exception as e:
            logging.error(f"Error creando/actualizando usuario: {str(e)}")
        
        # Crear o actualizar curso en la base de datos
        try:
            course_id = lti_launch_data.get('context_id', '')
            course_title = lti_launch_data.get('context_title', '')
            
            if course_id and course_title:
                course = CourseService.create_or_update_course(
                    course_id=course_id,
                    title=course_title,
                    moodle_id=moodle_instance_id
                )
                logging.info(f"Curso creado/actualizado: {course.id} - {course.title}")
                if moodle_instance_id:
                    logging.info(f"Curso asociado con instancia Moodle: {moodle_instance_id}")
        except Exception as e:
            logging.error(f"Error creando/actualizando curso: {str(e)}")
        
        logging.info("Sesión LTI creada")
        
        # Determinar URL de redirección según rol y existencia de actividad
        redirect_url = "/"
        
        roles = lti_launch_data.get('roles', '').lower()
        is_teacher_or_admin = any(role in roles for role in ['administrator', 'instructor', 'teacher', 'admin'])
        
        if is_teacher_or_admin:
            resource_link_id = lti_launch_data.get('resource_link_id', '')
            
            if resource_link_id and moodle_instance_id:
                from activities_service import ActivitiesService
                try:
                    activity = ActivitiesService.get_activity_by_id(resource_link_id, moodle_instance_id)
                    if not activity:
                        redirect_url = "/"
                        logging.info(f"Actividad '{resource_link_id}' no encontrada, redirigiendo a crear actividad")
                    else:
                        redirect_url = f"/actividad/{resource_link_id}"
                        logging.info(f"Actividad '{resource_link_id}' encontrada, redirigiendo a entregas")
                except Exception as e:
                    logging.error(f"Error verificando existencia de actividad: {str(e)}")
                    redirect_url = "/"
        # Add session_id to redirect URL as fallback for iframe cookie issues
        # This allows the frontend to capture it and use sessionStorage
        separator = "&" if "?" in redirect_url else "?"
        redirect_url_with_session = f"{redirect_url}{separator}lti_session={session_id}"
        
        response = RedirectResponse(url=redirect_url_with_session, status_code=303)
        
        is_https = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
        # For LTI in iframes, we need SameSite=None to allow cross-site cookies
        # SameSite=None requires Secure=True (HTTPS)
        # If not using HTTPS, fall back to Lax (will have issues in iframes)
        samesite_policy = "none" if is_https else "lax"
        response.set_cookie(
            key="lti_session",
            value=session_id,
            httponly=True,
            secure=is_https,
            samesite=samesite_policy,
            max_age=3600
        )
        
        return response
        
    except Exception as e:
        logging.error(f"Error procesando lanzamiento LTI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando lanzamiento LTI: {str(e)}")

def get_session_id_from_request(request: Request) -> str | None:
    """Extract session ID from cookie, header, or query param (fallback for iframe issues)"""
    # Try cookie first
    session_id = request.cookies.get("lti_session")
    if session_id:
        return session_id
    
    # Try X-LTI-Session header (for API calls from frontend)
    session_id = request.headers.get("X-LTI-Session")
    if session_id:
        return session_id
    
    # Try query parameter (last resort)
    session_id = request.query_params.get("lti_session")
    return session_id

@app.get("/api/lti-data")
async def get_current_session_data(request: Request):
    """Obtiene los datos LTI de la sesión actual"""
    try:
        session_id = get_session_id_from_request(request)
        
        # Debug logging for session issues
        logging.debug(f"Request cookies: {request.cookies}")
        logging.debug(f"X-LTI-Session header: {request.headers.get('X-LTI-Session')}")
        logging.debug(f"Session ID resolved: {session_id}")
        logging.debug(f"Available sessions in store: {list(lti_data_store.keys())}")
        
        if not session_id:
            logging.warning("No lti_session found in cookie, header, or query param")
            raise HTTPException(status_code=401, detail="No se encontró sesión LTI activa")
        
        if session_id not in lti_data_store:
            raise HTTPException(status_code=404, detail="Sesión expirada o no encontrada")
        
        return {
            "success": True,
            "session_id": session_id,
            "data": lti_data_store[session_id]
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo datos LTI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos LTI: {str(e)}")

@app.get("/api/debug-mode")
async def get_debug_mode(request: Request):
    """Returns whether debug mode is enabled (only for instructors/teachers)
    
    Debug mode shows raw AI responses for evaluation troubleshooting.
    Only returns true if DEBUG=true in environment AND user is an instructor.
    """
    try:
        session_id = get_session_id_from_request(request)
        if not session_id:
            return {"debug_mode": False}
        
        if session_id not in lti_data_store:
            return {"debug_mode": False}
        
        lti_data = lti_data_store[session_id]
        
        # Only show debug mode to instructors/teachers
        roles = lti_data.get('roles', '').lower()
        is_instructor = 'instructor' in roles or 'teacher' in roles or 'admin' in roles
        
        if not is_instructor:
            return {"debug_mode": False}
        
        # Check environment variable
        debug_enabled = os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')
        
        return {"debug_mode": debug_enabled}
        
    except Exception as e:
        logging.error(f"Error checking debug mode: {str(e)}")
        return {"debug_mode": False}

@app.get("/api/downloads/{file_path:path}")
async def download_file(file_path: str, request: Request):
    """Descarga archivos subidos (solo para profesores/administradores)"""
    try:
        session_id = get_session_id_from_request(request)
        if not session_id:
            raise HTTPException(status_code=401, detail="No se encontró sesión LTI activa")
        
        if session_id not in lti_data_store:
            raise HTTPException(status_code=404, detail="Sesión expirada o no encontrada")
        
        lti_data = lti_data_store[session_id]
        
        if not lti_data or not lti_data.get('roles'):
            raise HTTPException(status_code=403, detail="Sin permisos para descargar archivos")
        
        roles = lti_data['roles'].lower()
        has_permission = any(role in roles for role in ['administrator', 'instructor', 'teacher', 'admin'])
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Solo profesores y administradores pueden descargar archivos")
        
        import urllib.parse
        decoded_path = urllib.parse.unquote(file_path)
        
        full_path = FileStorageService.resolve_path(decoded_path)
        
        if not FileStorageService.is_within_uploads(full_path):
            raise HTTPException(status_code=403, detail="Acceso denegado al archivo")
        
        if not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        filename = os.path.basename(full_path)
        db = None
        try:
            db = get_db_session()
            file_submission = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.file_path == decoded_path
            ).first()
            
            if file_submission:
                extension = os.path.splitext(file_submission.file_name or "")[1]
                if not extension:
                    extension = os.path.splitext(filename)[1]
                
                if file_submission.group_code:
                    base_name = file_submission.group_code
                else:
                    student_submission = db.query(StudentSubmissionDB).filter(
                        StudentSubmissionDB.file_submission_id == file_submission.id
                    ).order_by(StudentSubmissionDB.joined_at.asc()).first()
                    
                    base_name = None
                    if student_submission:
                        user = db.query(UserDB).filter(UserDB.id == student_submission.student_id).first()
                        base_name = (user.full_name or "").strip()
                        if not base_name:
                            base_name = student_submission.student_id
                    if not base_name:
                        base_name = file_submission.uploaded_by or "submission"
                
                sanitized = FileStorageService.sanitize_filename(f"{base_name}{extension}")
                if sanitized:
                    filename = sanitized
        except Exception as e:
            logging.warning(f"Unable to customize download filename: {e}")
        finally:
            if db:
                db.close()
        
        return FileResponse(
            path=full_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error descargando archivo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error descargando archivo")

# Manejador de rutas SPA
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    """Sirve la aplicación SPA de Svelte"""
    try:
        if full_path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404, detail="Endpoint API no encontrado")
        
        if '.' in full_path.split('/')[-1] and not full_path.endswith(".html"):
            if full_path.startswith(('/app/', '/img/')):
                raise HTTPException(status_code=404, detail="Recurso estático no encontrado")
            else:
                raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        if os.path.isfile(frontend_index_html):
            return FileResponse(frontend_index_html)
        else:
            return HTMLResponse(
                content="<h1>Frontend no construido</h1><p>Por favor ejecuta 'npm run build' en el directorio frontend/svelte-app</p>",
                status_code=503
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error sirviendo SPA: {str(e)}")
        raise HTTPException(status_code=500, detail="Error sirviendo aplicación")