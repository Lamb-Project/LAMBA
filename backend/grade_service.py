import uuid
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from models import Grade, GradeRequest
from db_models import GradeDB, FileSubmissionDB, ActivityDB
from database import get_db_session
from document_extractor import DocumentExtractor
from lamb_api_service import LAMBAPIService

class GradeService:
    
    @staticmethod
    def create_grade(grade_request: GradeRequest) -> Grade:
        """Create a new grade for a file submission"""
        db = get_db_session()
        try:
            # Check if file submission exists
            file_submission = db.query(FileSubmissionDB).filter(FileSubmissionDB.id == grade_request.file_submission_id).first()
            if not file_submission:
                raise ValueError("File submission not found")
            
            # Check if grade already exists for this file submission
            existing_grade = db.query(GradeDB).filter(GradeDB.file_submission_id == grade_request.file_submission_id).first()
            if existing_grade:
                # Update existing grade
                existing_grade.score = grade_request.score
                existing_grade.comment = grade_request.comment
                db.commit()
                
                return Grade(
                    id=existing_grade.id,
                    file_submission_id=existing_grade.file_submission_id,
                    score=existing_grade.score,
                    comment=existing_grade.comment,
                    created_at=existing_grade.created_at
                )
            
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
            
            return Grade(
                id=db_grade.id,
                file_submission_id=db_grade.file_submission_id,
                score=db_grade.score,
                comment=db_grade.comment,
                created_at=db_grade.created_at
            )
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
            
            return Grade(
                id=db_grade.id,
                file_submission_id=db_grade.file_submission_id,
                score=db_grade.score,
                comment=db_grade.comment,
                created_at=db_grade.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def create_or_update_grade(file_submission_id: str, score: float, comment: Optional[str] = None) -> Grade:
        """Create or update a grade for a file submission
        
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
                # Update existing grade
                existing_grade.score = score
                existing_grade.comment = comment
                db.commit()
                db.refresh(existing_grade)
                
                return Grade(
                    id=existing_grade.id,
                    file_submission_id=existing_grade.file_submission_id,
                    score=existing_grade.score,
                    comment=existing_grade.comment,
                    created_at=existing_grade.created_at
                )
            
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
            
            return Grade(
                id=db_grade.id,
                file_submission_id=db_grade.file_submission_id,
                score=db_grade.score,
                comment=db_grade.comment,
                created_at=db_grade.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def create_automatic_evaluation_for_activity(activity_id: str, activity_moodle_id: str, file_submission_ids: list = None) -> List[Grade]:
        """
        Create grades for submissions in an activity using LAMB evaluation.
        Requires evaluator_id to be configured for the activity.

        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
            file_submission_ids: Optional list of specific file submission IDs to evaluate.
                                If None, evaluates all submissions without grades.
        """
        db = get_db_session()
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
            
            # If specific file_submission_ids provided, filter by them and exclude already graded
            if file_submission_ids:
                file_submissions = query.filter(
                    FileSubmissionDB.id.in_(file_submission_ids),
                    ~FileSubmissionDB.id.in_(
                        db.query(GradeDB.file_submission_id).filter(GradeDB.file_submission_id.isnot(None))
                    )
                ).all()
                logging.info(f"Evaluating {len(file_submissions)} specific submissions (ungraded)")
            else:
                # Otherwise, get all file submissions without grades
                file_submissions = query.filter(
                    ~FileSubmissionDB.id.in_(
                        db.query(GradeDB.file_submission_id).filter(GradeDB.file_submission_id.isnot(None))
                    )
                ).all()

            if not file_submissions:
                logging.info(f"No submissions to evaluate for activity {activity_id}")
                return []

            logging.info(f"Processing {len(file_submissions)} submissions with LAMB")
            created_grades = []
            errors = []

            for file_submission in file_submissions:
                try:
                    # LAMB-based evaluation
                    grade_result = GradeService._evaluate_with_lamb(
                        file_submission,
                        activity.evaluator_id
                    )
                    
                    # Create grade in database
                    grade_id = str(uuid.uuid4())
                    db_grade = GradeDB(
                        id=grade_id,
                        file_submission_id=file_submission.id,
                        score=grade_result['score'],
                        comment=grade_result['comment'],
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    db.add(db_grade)
                    
                    # Create grade model for response
                    grade = Grade(
                        id=grade_id,
                        file_submission_id=file_submission.id,
                        score=grade_result['score'],
                        comment=grade_result['comment'],
                        created_at=datetime.now(timezone.utc)
                    )
                    created_grades.append(grade)
                    
                    logging.info(f"Grade created for submission {file_submission.id}: {grade_result['score']}/10")
                    
                except Exception as e:
                    error_msg = f"Error evaluating submission {file_submission.id}: {str(e)}"
                    logging.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            db.commit()
            
            # Log summary
            if errors:
                logging.warning(f"Completed with {len(errors)} errors: {'; '.join(errors)}")
            
            return created_grades
            
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
            Dictionary with score and comment
        """
        # Get absolute path to file
        # Assuming file_path is relative to uploads directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_abs_path = os.path.join(base_dir, file_submission.file_path)
        
        logging.info(f"Extracting text from: {file_abs_path}")
        
        # Extract text from document
        extracted_text = DocumentExtractor.extract_text_from_file(file_abs_path)
        
        if not extracted_text or not extracted_text.strip():
            logging.warning(f"Could not extract text from {file_submission.file_name}")
            return {
                'score': 5.0,
                'comment': "No se pudo extraer texto del documento para evaluar. Verifica el formato del archivo."
            }
        
        logging.info(f"Extracted {len(extracted_text)} characters from document")
        
        # Send to LAMB for evaluation
        lamb_result = LAMBAPIService.evaluate_text(extracted_text, evaluator_id)
        
        if not lamb_result['success']:
            logging.error(f"LAMB evaluation failed: {lamb_result['error']}")
            return {
                'score': 5.0,
                'comment': f"Error en la evaluación automática: {lamb_result['error']}"
            }
        
        # Parse LAMB response
        parsed = LAMBAPIService.parse_evaluation_response(lamb_result['response'])
        
        score = parsed.get('score', 7.0)
        comment = parsed.get('comment', 'Evaluación completada')
        
        # Ensure score is in valid range
        score = max(0.0, min(10.0, score))
        
        return {
            'score': score,
            'comment': comment
        }