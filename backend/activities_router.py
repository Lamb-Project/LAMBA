from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from typing import List
import logging

from models import Activity, ActivityCreate, ActivityUpdate, ActivityResponse, StudentActivityView, SubmissionResponse, OptimizedSubmissionView
from activities_service import ActivitiesService
from lti_service import LTIGradeService
from grade_service import GradeService

router = APIRouter()

def get_lti_session_data(request: Request) -> dict:
    """Get LTI data from session cookie"""
    session_id = request.cookies.get("lti_session")
    if not session_id:
        raise HTTPException(status_code=401, detail="No se encontró sesión LTI activa")
    
    from main import lti_data_store
    
    if session_id not in lti_data_store:
        raise HTTPException(status_code=404, detail="Sesión expirada o no encontrada")
    
    return lti_data_store[session_id]

def check_teacher_role(lti_data: dict) -> bool:
    """Check if user has admin or teacher role"""
    if not lti_data or not lti_data.get('roles'):
        return False
    
    roles = lti_data['roles'].lower()
    return any(role in roles for role in ['administrator', 'instructor', 'teacher', 'admin'])

def check_student_role(lti_data: dict) -> bool:
    """Check if user has student role"""
    if not lti_data or not lti_data.get('roles'):
        return False
    
    roles = lti_data['roles'].lower()
    return 'learner' in roles or 'student' in roles

# ==================== CRUD de Actividades ====================

@router.post("", response_model=ActivityResponse)
async def create_activity(activity_data: ActivityCreate, request: Request):
    """Crea una nueva actividad"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden crear actividades")
        
        resource_link_id = lti_data.get('resource_link_id', '')
        if not resource_link_id:
            raise HTTPException(status_code=400, detail="No se encontró resource_link_id en los datos LTI")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        activity = ActivitiesService.create_activity(
            activity_data=activity_data,
            user_id=lti_data.get('user_id', ''),
            course_id=lti_data.get('context_id', ''),
            course_moodle_id=moodle_id,
            activity_id=resource_link_id
        )
        
        logging.info(f"Actividad creada: {activity.id} por usuario {lti_data.get('user_id')}")
        
        return ActivityResponse(
            success=True,
            message="Actividad creada exitosamente",
            activity=activity
        )
        
    except HTTPException:
        # Propagar errores HTTP tal cual (p.ej. 403 de autorización)
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creando actividad: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{activity_id}", response_model=Activity)
async def get_activity(activity_id: str, request: Request):
    """Obtiene una actividad específica por ID"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden ver actividades")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        activity = ActivitiesService.get_activity_by_id(activity_id, moodle_id)
        
        if not activity:
            raise HTTPException(status_code=404, detail="Actividad no encontrada")
        
        return activity
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo actividad: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{activity_id}")
async def update_activity(activity_id: str, activity_data: ActivityUpdate, request: Request):
    """Actualiza una actividad existente"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden actualizar actividades")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        course_id = lti_data.get('context_id', '')
        
        activity = ActivitiesService.update_activity(
            activity_id=activity_id,
            activity_moodle_id=moodle_id,
            activity_data=activity_data,
            user_id=lti_data.get('user_id', ''),
            user_moodle_id=moodle_id,
            course_id=course_id
        )
        
        logging.info(f"Actividad actualizada: {activity_id} por usuario {lti_data.get('user_id')}")
        
        return ActivityResponse(
            success=True,
            message="Actividad actualizada exitosamente",
            activity=activity
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error actualizando actividad: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==================== Vista de Estudiante ====================

@router.get("/{activity_id}/view", response_model=StudentActivityView)
async def get_student_activity_view(activity_id: str, request: Request):
    """Obtiene la vista de una actividad para el estudiante (actividad + su entrega)"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden acceder a esta vista")
        
        student_id = lti_data.get('user_id', '')
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        student_view = ActivitiesService.get_student_activity_view_by_id(
            resource_link_id=activity_id,
            moodle_id=moodle_id,
            student_id=student_id,
            student_moodle_id=moodle_id
        )
        
        return student_view
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo vista de estudiante: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==================== Entregas de una Actividad ====================

@router.post("/{activity_id}/submissions", response_model=SubmissionResponse)
async def create_submission(
    activity_id: str,
    request: Request,
    file: UploadFile = File(...)
):
    """Crea una nueva entrega para una actividad"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_student_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo estudiantes pueden entregar trabajos")
        
        lis_result_sourcedid = lti_data.get('lis_result_sourcedid')
        logging.info(f"Procesando entrega - Estudiante: {lti_data.get('user_id')}, LIS Result SourcedID: {lis_result_sourcedid}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No se seleccionó ningún archivo")
        
        # Verificar tamaño (max 50MB)
        max_size = 50 * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máximo 50MB)")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        student_moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        
        submission = ActivitiesService.create_submission(
            activity_id=activity_id,
            student_id=lti_data.get('user_id', ''),
            student_name=lti_data.get('lis_person_name_full', '') or lti_data.get('ext_user_username', ''),
            student_email=lti_data.get('lis_person_contact_email_primary'),
            file_name=file.filename,
            file_content=file_content,
            file_size=len(file_content),
            file_type=file.content_type or 'application/octet-stream',
            course_id=lti_data.get('context_id', ''),
            course_moodle_id=moodle_id,
            student_moodle_id=student_moodle_id,
            lis_result_sourcedid=lti_data.get('lis_result_sourcedid')
        )
        
        logging.info(f"Documento entregado: {submission.student_submission.id} por estudiante {lti_data.get('user_id')}")
        
        return SubmissionResponse(
            success=True,
            message="Documento enviado exitosamente",
            submission=submission
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error enviando documento: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{activity_id}/submissions")
async def get_activity_submissions(activity_id: str, request: Request):
    """Obtiene todas las entregas de una actividad (para profesores)"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden ver entregas")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        submissions_data = ActivitiesService.get_submissions_by_activity(activity_id, moodle_id)
        
        return submissions_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo entregas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==================== Evaluación Automática ====================

@router.post("/{activity_id}/evaluate")
async def evaluate_activity(activity_id: str, request: Request):
    """Evalúa automáticamente entregas de una actividad usando LAMB
    
    Acepta un JSON con un array opcional de file_submission_ids.
    Si no se proporciona, evalúa todas las entregas sin calificación.
    """
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden evaluar actividades")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        # Try to parse request body for file_submission_ids
        file_submission_ids = None
        try:
            body = await request.json()
            file_submission_ids = body.get('file_submission_ids')
        except:
            pass
        
        logging.info(f"Iniciando evaluación automática de actividad {activity_id}")
        if file_submission_ids:
            logging.info(f"Evaluando {len(file_submission_ids)} entregas específicas")
        
        results = GradeService.create_automatic_evaluation_for_activity(activity_id, moodle_id, file_submission_ids)
        
        logging.info(f"Evaluación automática completada para actividad {activity_id}: {len(results)} calificaciones creadas")
        
        return {
            "success": True,
            "message": "Evaluación automática completada exitosamente" if len(results) > 0 else "No hay entregas pendientes de evaluar",
            "grades_created": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en evaluación automática: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==================== Sincronización de Calificaciones ====================

@router.post("/{activity_id}/grades/sync")
async def sync_grades_to_moodle(activity_id: str, request: Request):
    """Sincroniza todas las calificaciones de una actividad con Moodle"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden enviar calificaciones")
        
        moodle_id = lti_data.get('tool_consumer_instance_guid', '')
        if not moodle_id:
            raise HTTPException(status_code=400, detail="No se encontró tool_consumer_instance_guid en los datos LTI")
        
        logging.info(f"Iniciando sincronización de calificaciones para actividad {activity_id}")
        
        result = LTIGradeService.send_activity_grades_to_moodle(activity_id, moodle_id)
        
        if not result.get('success'):
            return {
                "success": False,
                "message": result.get('error', 'Error al enviar calificaciones'),
                "details": result
            }
        
        logging.info(f"Calificaciones sincronizadas: {result.get('sent_count')}/{result.get('total_submissions')}")
        
        return {
            "success": True,
            "message": f"Calificaciones enviadas: {result.get('sent_count')}/{result.get('total_submissions')}",
            "details": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error sincronizando calificaciones: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
