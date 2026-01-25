import uuid
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models import Grade, GradeRequest
from db_models import GradeDB, FileSubmissionDB, ActivityDB
from database import get_db_session
from document_extractor import DocumentExtractor
from lamb_api_service import LAMBAPIService

def is_debug_mode() -> bool:
    """Check if debug mode is enabled via environment variable"""
    return os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes')

class GradeService:
    
    @staticmethod
    def _db_grade_to_model(db_grade: GradeDB) -> Grade:
        """Convert database grade to model"""
        return Grade(
            id=db_grade.id,
            file_submission_id=db_grade.file_submission_id,
            ai_score=db_grade.ai_score,
            ai_comment=db_grade.ai_comment,
            ai_evaluated_at=db_grade.ai_evaluated_at,
            score=db_grade.score,
            comment=db_grade.comment,
            created_at=db_grade.created_at,
            updated_at=db_grade.updated_at
        )
    
    @staticmethod
    def create_grade(grade_request: GradeRequest) -> Grade:
        """Create a new grade for a file submission (sets final grade)"""
        db = get_db_session()
        try:
            # Check if file submission exists
            file_submission = db.query(FileSubmissionDB).filter(FileSubmissionDB.id == grade_request.file_submission_id).first()
            if not file_submission:
                raise ValueError("File submission not found")
            
            # Check if grade already exists for this file submission
            existing_grade = db.query(GradeDB).filter(GradeDB.file_submission_id == grade_request.file_submission_id).first()
            if existing_grade:
                # Update existing grade (final grade only)
                existing_grade.score = grade_request.score
                existing_grade.comment = grade_request.comment
                existing_grade.updated_at = datetime.now(timezone.utc)
                db.commit()
                
                return GradeService._db_grade_to_model(existing_grade)
            
            # Create new grade
            grade_id = str(uuid.uuid4())
            db_grade = GradeDB(
                id=grade_id,
                file_submission_id=grade_request.file_submission_id,
                score=grade_request.score,
                comment=grade_request.comment,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(db_grade)
            db.commit()
            db.refresh(db_grade)
            
            return GradeService._db_grade_to_model(db_grade)
        finally:
            db.close()
    
    @staticmethod
    def get_grade_by_file_submission(file_submission_id: str) -> Optional[Grade]:
        """Get grade for a specific file submission"""
        db = get_db_session()
        try:
            db_grade = db.query(GradeDB).filter(GradeDB.file_submission_id == file_submission_id).first()
            if not db_grade:
                return None
            
            return GradeService._db_grade_to_model(db_grade)
        finally:
            db.close()
    
    @staticmethod
    def create_or_update_grade(file_submission_id: str, score: float, comment: Optional[str] = None) -> Grade:
        """Create or update the final grade for a file submission (professor's grade)
        
        Raises:
            FileNotFoundError: If the file submission doesn't exist
        """
        db = get_db_session()
        try:
            # Check if file submission exists
            file_submission = db.query(FileSubmissionDB).filter(FileSubmissionDB.id == file_submission_id).first()
            if not file_submission:
                raise FileNotFoundError("Entrega no encontrada")
            
            # Check if grade already exists for this file submission
            existing_grade = db.query(GradeDB).filter(GradeDB.file_submission_id == file_submission_id).first()
            if existing_grade:
                # Update existing grade (final grade only, preserve AI grade)
                existing_grade.score = score
                existing_grade.comment = comment
                existing_grade.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(existing_grade)
                
                return GradeService._db_grade_to_model(existing_grade)
            
            # Create new grade
            grade_id = str(uuid.uuid4())
            db_grade = GradeDB(
                id=grade_id,
                file_submission_id=file_submission_id,
                score=score,
                comment=comment,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(db_grade)
            db.commit()
            db.refresh(db_grade)
            
            return GradeService._db_grade_to_model(db_grade)
        finally:
            db.close()
    
    @staticmethod
    def create_automatic_evaluation_for_activity(activity_id: str, activity_moodle_id: str, file_submission_ids: list = None) -> Dict[str, Any]:
        """
        Create grades for submissions in an activity using LAMB evaluation.
        Requires evaluator_id to be configured for the activity.

        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
            file_submission_ids: Optional list of specific file submission IDs to evaluate.
                                If None, evaluates all submissions without grades.
        
        Returns:
            Dictionary with 'grades' list and 'debug_info' list (when DEBUG=true)
        """
        db = get_db_session()
        debug_mode = is_debug_mode()
        
        try:
            # Get activity to check if evaluator_id is configured (using composite key)
            activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == activity_moodle_id
            ).first()
            if not activity:
                raise ValueError("Actividad no encontrada")
            
            # Check that evaluator_id is configured
            if not activity.evaluator_id:
                raise ValueError("Esta actividad no tiene configurado un ID de evaluador. Configure el ID del evaluador en la configuración de la actividad para poder usar la evaluación automática.")
            
            # Verify LAMB model exists
            verification = LAMBAPIService.verify_model_exists(activity.evaluator_id)
            if not verification["success"]:
                raise ValueError(verification["error"])
            
            logging.info(f"Using LAMB model {verification['model_id']} for evaluation")
            
            # Get file submissions to evaluate
            query = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.activity_id == activity_id,
                FileSubmissionDB.activity_moodle_id == activity_moodle_id
            )
            
            # If specific file_submission_ids provided, filter by them
            # NOTE: We now allow re-evaluation of already graded submissions
            if file_submission_ids:
                file_submissions = query.filter(
                    FileSubmissionDB.id.in_(file_submission_ids)
                ).all()
                logging.info(f"Evaluating {len(file_submissions)} specific submissions (including previously graded)")
            else:
                # Otherwise, get all file submissions (including those with grades for re-evaluation)
                file_submissions = query.all()
                logging.info(f"Evaluating all {len(file_submissions)} submissions for activity")

            if not file_submissions:
                logging.info(f"No submissions found for activity {activity_id}")
                return {
                    'grades': [], 
                    'debug_info': [] if debug_mode else None,
                    'message': 'No submissions found for this activity'
                }
            
            # Check which submissions already have grades (for reporting)
            existing_grade_ids = set(
                row[0] for row in db.query(GradeDB.file_submission_id).filter(
                    GradeDB.file_submission_id.in_([fs.id for fs in file_submissions])
                ).all()
            )
            re_evaluation_count = len(existing_grade_ids)

            logging.info(f"Processing {len(file_submissions)} submissions with LAMB ({re_evaluation_count} re-evaluations)")
            created_grades = []
            updated_grades = []
            debug_info_list = [] if debug_mode else None
            errors = []

            for file_submission in file_submissions:
                try:
                    # LAMB-based evaluation
                    grade_result = GradeService._evaluate_with_lamb(
                        file_submission,
                        activity.evaluator_id
                    )
                    
                    # Collect debug info if in debug mode
                    if debug_mode and grade_result.get('debug_info'):
                        debug_info_list.append(grade_result['debug_info'])
                    
                    # Check if grade already exists for this submission
                    existing_grade = db.query(GradeDB).filter(
                        GradeDB.file_submission_id == file_submission.id
                    ).first()
                    
                    if existing_grade:
                        # Update existing grade
                        existing_grade.score = grade_result['score']
                        existing_grade.comment = grade_result['comment']
                        existing_grade.created_at = datetime.now(timezone.utc)  # Update timestamp
                        
                        grade = Grade(
                            id=existing_grade.id,
                            file_submission_id=file_submission.id,
                            score=grade_result['score'],
                            comment=grade_result['comment'],
                            created_at=datetime.now(timezone.utc)
                        )
                        updated_grades.append(grade)
                        logging.info(f"Grade UPDATED for submission {file_submission.id}: {grade_result['score']}/10")
                    else:
                        # Create new grade
                        grade_id = str(uuid.uuid4())
                        db_grade = GradeDB(
                            id=grade_id,
                            file_submission_id=file_submission.id,
                            score=grade_result['score'],
                            comment=grade_result['comment'],
                            created_at=datetime.now(timezone.utc)
                        )
                        db.add(db_grade)
                        
                        grade = Grade(
                            id=grade_id,
                            file_submission_id=file_submission.id,
                            score=grade_result['score'],
                            comment=grade_result['comment'],
                            created_at=datetime.now(timezone.utc)
                        )
                        created_grades.append(grade)
                        logging.info(f"Grade CREATED for submission {file_submission.id}: {grade_result['score']}/10")
                    
                except Exception as e:
                    error_msg = f"Error evaluating submission {file_submission.id}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            db.commit()
            
            # Log summary
            if errors:
                logging.warning(f"Completed with {len(errors)} errors: {'; '.join(errors)}")
            
            return {
                'grades': created_grades,
                'updated_grades': updated_grades,
                'debug_info': debug_info_list,
                'errors': errors if errors else None
            }
            
        finally:
            db.close()
    
    @staticmethod
    def _evaluate_with_lamb(file_submission: FileSubmissionDB, evaluator_id: str) -> dict:
        """
        Evaluate a file submission using LAMB API
        
        Args:
            file_submission: File submission to evaluate
            evaluator_id: LAMB evaluator ID
            
        Returns:
            Dictionary with score, comment, and debug_info (when DEBUG=true)
        """
        debug_info = None
        if is_debug_mode():
            debug_info = {
                'file_name': file_submission.file_name,
                'file_submission_id': file_submission.id,
                'evaluator_id': evaluator_id,
                'extracted_text': None,
                'lamb_raw_response': None,
                'parsed_response': None
            }
        
        # Get absolute path to file
        # Assuming file_path is relative to uploads directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_abs_path = os.path.join(base_dir, file_submission.file_path)
        
        logging.info(f"Extracting text from: {file_abs_path}")
        
        # Extract text from document
        extracted_text = DocumentExtractor.extract_text_from_file(file_abs_path)
        
        if debug_info:
            # Truncate extracted text for debug to avoid huge responses
            debug_info['extracted_text'] = extracted_text[:2000] + '...' if extracted_text and len(extracted_text) > 2000 else extracted_text
        
        if not extracted_text or not extracted_text.strip():
            logging.warning(f"Could not extract text from {file_submission.file_name}")
            return {
                'score': 5.0,
                'comment': "No se pudo extraer texto del documento para evaluar. Verifica el formato del archivo.",
                'debug_info': debug_info
            }
        
        logging.info(f"Extracted {len(extracted_text)} characters from document")
        
        # Send to LAMB for evaluation
        lamb_result = LAMBAPIService.evaluate_text(extracted_text, evaluator_id)
        
        if debug_info:
            debug_info['lamb_raw_response'] = lamb_result.get('response') if lamb_result.get('success') else lamb_result.get('error')
        
        if not lamb_result['success']:
            logging.error(f"LAMB evaluation failed: {lamb_result['error']}")
            return {
                'score': 5.0,
                'comment': f"Error en la evaluación automática: {lamb_result['error']}",
                'debug_info': debug_info
            }
        
        # Parse LAMB response
        parsed = LAMBAPIService.parse_evaluation_response(lamb_result['response'])
        
        if debug_info:
            debug_info['parsed_response'] = parsed
            # Add JSON validation results as a top-level field for easy access
            debug_info['json_validation'] = parsed.get('json_validation', {})
        
        score = parsed.get('score', 7.0)
        comment = parsed.get('comment', 'Evaluación completada')
        
        # Ensure score is in valid range
        score = max(0.0, min(10.0, score))
        
        return {
            'score': score,
            'comment': comment,
            'debug_info': debug_info
        }