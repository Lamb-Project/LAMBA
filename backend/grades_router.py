from fastapi import APIRouter, HTTPException, Request
import logging

from models import GradeRequest, GradeUpdate, GradeResponse
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
    """Check if user has teacher/admin role"""
    if not lti_data or not lti_data.get('roles'):
        return False
    
    roles = lti_data['roles'].lower()
    return any(role in roles for role in ['administrator', 'instructor', 'teacher', 'admin'])

@router.post("/{submission_id}", response_model=GradeResponse)
async def grade_submission(submission_id: str, grade_data: GradeUpdate, request: Request):
    """Califica una entrega específica"""
    try:
        lti_data = get_lti_session_data(request)
        
        if not check_teacher_role(lti_data):
            raise HTTPException(status_code=403, detail="Solo profesores pueden calificar")
        
        # Validar la nota
        if grade_data.score < 0 or grade_data.score > 10:
            raise HTTPException(status_code=400, detail="La nota debe estar entre 0 y 10")
        
        # Usar el submission_id del path en lugar del body
        grade = GradeService.create_or_update_grade(
            file_submission_id=submission_id,
            score=grade_data.score,
            comment=grade_data.comment
        )
        
        logging.info(f"Calificación creada/actualizada para entrega {submission_id}: {grade_data.score}/10")
        
        return GradeResponse(
            success=True,
            message="Calificación guardada exitosamente",
            grade=grade
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al calificar entrega: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

