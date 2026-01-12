"""
Router for admin endpoints.
Provides authentication and data endpoints for the admin dashboard.
"""

from fastapi import APIRouter, HTTPException, Request, Response
import os
import hashlib
from datetime import datetime, timedelta
from admin_service import AdminService

router = APIRouter()

# Simple in-memory session store for admin sessions
# In production, use a proper session management system or JWT
admin_sessions = {}

def create_admin_session(username: str) -> str:
    """
    Create an admin session and return the session ID
    
    Args:
        username: Admin username
        
    Returns:
        str: Session ID
    """
    session_id = hashlib.sha256(
        f"{username}_{datetime.utcnow().isoformat()}_{os.urandom(16).hex()}".encode()
    ).hexdigest()
    
    admin_sessions[session_id] = {
        "username": username,
        "created_at": datetime.utcnow(),
        "last_accessed": datetime.utcnow()
    }
    
    return session_id


def verify_admin_session(request: Request) -> bool:
    """
    Verify if the request has a valid admin session
    
    Args:
        request: FastAPI request object
        
    Returns:
        bool: True if session is valid, False otherwise
    """
    session_id = request.cookies.get("admin_session")
    
    if not session_id or session_id not in admin_sessions:
        return False
    
    session = admin_sessions[session_id]
    
    # Check if session has expired (24 hours)
    if datetime.utcnow() - session["created_at"] > timedelta(hours=24):
        del admin_sessions[session_id]
        return False
    
    # Update last accessed time
    session["last_accessed"] = datetime.utcnow()
    
    return True


@router.post("/api/admin/login")
async def admin_login(request: Request, response: Response):
    """
    Admin login endpoint.
    Expects JSON body with username and password.
    
    Returns:
        - 200: Login successful, session cookie set
        - 401: Invalid credentials
    """
    try:
        body = await request.json()
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Usuario y contraseña requeridos")
        
        if not AdminService.verify_admin_credentials(username, password):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        session_id = create_admin_session(username)
        
        is_https = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
        response.set_cookie(
            key="admin_session",
            value=session_id,
            httponly=True,
            secure=is_https,
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        return {
            "success": True,
            "message": "Inicio de sesión exitoso"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")


@router.post("/api/admin/logout")
async def admin_logout(request: Request, response: Response):
    """
    Admin logout endpoint.
    Clears the admin session.
    
    Returns:
        - 200: Logout successful
    """
    try:
        session_id = request.cookies.get("admin_session")
        
        if session_id and session_id in admin_sessions:
            del admin_sessions[session_id]
        
        response.delete_cookie(
            key="admin_session",
            httponly=True,
            samesite="lax"
        )
        
        return {
            "success": True,
            "message": "Sesión cerrada"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")


@router.get("/api/admin/check-session")
async def check_admin_session(request: Request):
    """
    Check if admin has a valid session.
    
    Returns:
        - 200: Session is valid
        - 401: No valid session
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="Sesión no válida")
    
    session_id = request.cookies.get("admin_session")
    session = admin_sessions.get(session_id)
    
    return {
        "success": True,
        "username": session.get("username") if session else None
    }


@router.get("/api/admin/statistics")
async def get_statistics(request: Request):
    """
    Get system statistics.
    Requires valid admin session.
    
    Returns:
        - 200: Statistics data
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        stats = AdminService.get_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.get("/api/admin/moodle-instances")
async def get_moodle_instances(request: Request):
    """
    Get all Moodle instances.
    Requires valid admin session.
    
    Returns:
        - 200: List of Moodle instances
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        moodles = AdminService.get_all_moodle_instances()
        return {
            "success": True,
            "data": moodles,
            "count": len(moodles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo instancias: {str(e)}")


@router.get("/api/admin/courses")
async def get_courses(request: Request):
    """
    Get all courses.
    Requires valid admin session.
    
    Returns:
        - 200: List of courses
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        courses = AdminService.get_all_courses()
        return {
            "success": True,
            "data": courses,
            "count": len(courses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo cursos: {str(e)}")


@router.get("/api/admin/activities")
async def get_activities(request: Request):
    """
    Get all activities.
    Requires valid admin session.
    
    Returns:
        - 200: List of activities
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        activities = AdminService.get_all_activities()
        return {
            "success": True,
            "data": activities,
            "count": len(activities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo actividades: {str(e)}")


@router.get("/api/admin/users")
async def get_users(request: Request):
    """
    Get all users.
    Requires valid admin session.
    
    Returns:
        - 200: List of users
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        users = AdminService.get_all_users()
        return {
            "success": True,
            "data": users,
            "count": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios: {str(e)}")


@router.get("/api/admin/submissions")
async def get_submissions(request: Request):
    """
    Get all student submissions.
    Requires valid admin session.
    
    Returns:
        - 200: List of submissions
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        submissions = AdminService.get_all_submissions()
        return {
            "success": True,
            "data": submissions,
            "count": len(submissions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo entregas: {str(e)}")


@router.get("/api/admin/files")
async def get_files(request: Request):
    """
    Get all file submissions.
    Requires valid admin session.
    
    Returns:
        - 200: List of files
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        files = AdminService.get_all_files()
        return {
            "success": True,
            "data": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo ficheros: {str(e)}")


@router.get("/api/admin/grades")
async def get_grades(request: Request):
    """
    Get all grades.
    Requires valid admin session.
    
    Returns:
        - 200: List of grades
        - 401: Unauthorized
    """
    if not verify_admin_session(request):
        raise HTTPException(status_code=401, detail="No autorizado")
    
    try:
        grades = AdminService.get_all_grades()
        return {
            "success": True,
            "data": grades,
            "count": len(grades)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo calificaciones: {str(e)}")
