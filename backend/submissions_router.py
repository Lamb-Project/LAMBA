from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import logging
import os
import urllib.parse

from models import GroupCodeSubmission, GroupCodeResponse, SubmissionResponse, OptimizedSubmissionView
from activities_service import ActivitiesService
from storage_service import FileStorageService
from database import get_db_session
from db_models import FileSubmissionDB, StudentSubmissionDB, UserDB

router = APIRouter()

def get_lti_session_data(request: Request) -> dict:
    """Get LTI data from session cookie, header, or query param (for iframe compatibility)"""
    # Try cookie first
    session_id = request.cookies.get("lti_session")
    
    # Try X-LTI-Session header (for API calls from frontend with sessionStorage fallback)
    if not session_id:
        session_id = request.headers.get("X-LTI-Session")
    
    # Try query parameter (last resort)
    if not session_id:
        session_id = request.query_params.get("lti_session")
    
    if not session_id:
        raise HTTPException(status_code=401, detail="No se encontró sesión LTI activa")
    
    from main import lti_data_store
    
    if session_id not in lti_data_store:
        raise HTTPException(status_code=404, detail="Sesión expirada o no encontrada")
    
    return lti_data_store[session_id]

def check_student_role(lti_data: dict) -> bool:
    """Check if user has student role"""
    if not lti_data or not lti_data.get('roles'):
        return False
    
    roles = lti_data['roles'].lower()
    return 'learner' in roles or 'student' in roles

@router.get("/me", response_model=Optional[OptimizedSubmissionView])
async def get_my_submission(request: Request):
    """Obtiene la entrega actual del estudiante para la actividad del contexto LTI"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden ver sus entregas")
        
        activity_id = lti_data.get('resource_link_id', '')
        if not activity_id:
            raise HTTPException(status_code=400, detail="No se encontró resource_link_id en los datos LTI")
        
        student_id = lti_data.get('user_id', '')
        activity_moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        student_moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        
        if not activity_moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        submission = ActivitiesService.get_student_submission(activity_id, activity_moodle_id, student_id, student_moodle_id)
        return submission
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo entrega del estudiante: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/join", response_model=GroupCodeResponse)
async def join_group(request: Request, code_data: GroupCodeSubmission):
    """Unirse a un grupo usando un código compartido"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden unirse a grupos")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        submission = ActivitiesService.submit_with_group_code(
            activity_id=code_data.activity_id,
            group_code=code_data.group_code.upper().strip(),
            student_id=lti_data.get('user_id', ''),
            student_name=lti_data.get('lis_person_name_full', '') or lti_data.get('ext_user_username', ''),
            student_email=lti_data.get('lis_person_contact_email_primary'),
            course_id=lti_data.get('context_id', ''),
            course_moodle_id=moodle_id,
            lis_result_sourcedid=lti_data.get('lis_result_sourcedid')
        )
        
        logging.info(f"Estudiante {lti_data.get('user_id')} se unió al grupo con código {code_data.group_code}")
        
        return GroupCodeResponse(
            success=True,
            message="Te has unido al grupo exitosamente",
            submission=submission
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uniéndose al grupo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{submission_id}/members")
async def get_submission_members(submission_id: str, request: Request):
    """Obtiene los miembros de una entrega grupal"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden ver miembros de grupos")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        # Obtener la entrega para obtener el group_code
        db = get_db_session()
        try:
            file_submission = db.query(FileSubmissionDB).filter(FileSubmissionDB.id == submission_id).first()
            
            if not file_submission or not file_submission.group_code:
                raise HTTPException(status_code=404, detail="Entrega grupal no encontrada")
            
            # Obtener todos los estudiantes que tienen este file_submission_id
            student_submissions = db.query(StudentSubmissionDB, UserDB).join(
                UserDB,
                (StudentSubmissionDB.student_id == UserDB.id) &
                (StudentSubmissionDB.student_moodle_id == UserDB.moodle_id)
            ).filter(
                StudentSubmissionDB.file_submission_id == submission_id
            ).order_by(StudentSubmissionDB.joined_at.asc()).all()
            
            members = []
            # El primer estudiante (ordenado por joined_at) es el líder del grupo
            for idx, (student_sub, user) in enumerate(student_submissions):
                members.append({
                    "student_id": student_sub.student_id,
                    "student_name": user.full_name,
                    "email": user.email,
                    "is_group_leader": idx == 0,  # El primero es el líder
                    "submitted_at": student_sub.joined_at.isoformat() + 'Z' if student_sub.joined_at else None
                })
            
            return members
            
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo miembros del grupo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/my-file/download")
async def download_my_submission_file(request: Request):
    """Permite a un estudiante descargar el archivo de su propia entrega (o la de su grupo)"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden descargar sus entregas")
        
        activity_id = lti_data.get('resource_link_id', '')
        if not activity_id:
            raise HTTPException(status_code=400, detail="No se encontró resource_link_id en los datos LTI")
        
        student_id = lti_data.get('user_id', '')
        activity_moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        student_moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        
        if not activity_moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        db = get_db_session()
        try:
            # Find the student's submission for this activity
            student_submission = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.activity_id == activity_id,
                StudentSubmissionDB.activity_moodle_id == activity_moodle_id,
                StudentSubmissionDB.student_id == student_id,
                StudentSubmissionDB.student_moodle_id == student_moodle_id
            ).first()
            
            if not student_submission:
                raise HTTPException(status_code=404, detail="No se encontró ninguna entrega para este estudiante")
            
            # Get the associated file submission (this works for both individual and group submissions)
            file_submission = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.id == student_submission.file_submission_id
            ).first()
            
            if not file_submission:
                raise HTTPException(status_code=404, detail="No se encontró el archivo de la entrega")
            
            # Resolve the file path
            file_path = file_submission.file_path
            decoded_path = urllib.parse.unquote(file_path)
            full_path = FileStorageService.resolve_path(decoded_path)
            
            # Security check: ensure file is within uploads directory
            if not FileStorageService.is_within_uploads(full_path):
                raise HTTPException(status_code=403, detail="Acceso denegado al archivo")
            
            if not os.path.isfile(full_path):
                raise HTTPException(status_code=404, detail="Archivo no encontrado en el sistema")
            
            # Use the original filename for download
            download_filename = file_submission.file_name or os.path.basename(full_path)
            
            logging.info(f"Student {student_id} downloading their submission file: {download_filename}")
            
            return FileResponse(
                path=full_path,
                filename=download_filename,
                media_type=file_submission.file_type or 'application/octet-stream'
            )
            
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error descargando archivo de entrega del estudiante: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
