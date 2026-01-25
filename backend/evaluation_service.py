"""
Evaluation Service - Manages background evaluation jobs

Handles:
- Starting background evaluations
- Tracking evaluation status
- Preventing duplicate evaluations
- Timeout handling for stuck evaluations
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from database import get_db_session
from db_models import FileSubmissionDB, GradeDB, ActivityDB
from grade_service import GradeService
from document_extractor import DocumentExtractor
from lamb_api_service import LAMBAPIService

# Evaluation status constants
STATUS_PENDING = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_COMPLETED = 'completed'
STATUS_ERROR = 'error'

# Timeout for stuck evaluations (5 minutes)
EVALUATION_TIMEOUT_MINUTES = 5


class EvaluationService:
    """Service for managing background evaluations"""
    
    @staticmethod
    def get_evaluation_status(activity_id: str, activity_moodle_id: str, file_submission_ids: List[str] = None) -> Dict[str, Any]:
        """Get current evaluation status for an activity's submissions
        
        Args:
            activity_id: Activity ID
            activity_moodle_id: Moodle instance ID
            file_submission_ids: Optional list of specific file submission IDs to check
            
        Returns:
            Dictionary with evaluation status information
        """
        db = get_db_session()
        try:
            query = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.activity_id == activity_id,
                FileSubmissionDB.activity_moodle_id == activity_moodle_id
            )
            
            if file_submission_ids:
                query = query.filter(FileSubmissionDB.id.in_(file_submission_ids))
            
            submissions = query.all()
            
            status_counts = {
                'total': len(submissions),
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'error': 0,
                'not_started': 0
            }
            
            submission_statuses = []
            
            for sub in submissions:
                status = sub.evaluation_status or 'not_started'
                
                # Check for timeout
                if status == STATUS_PROCESSING and sub.evaluation_started_at:
                    timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=EVALUATION_TIMEOUT_MINUTES)
                    started_at = sub.evaluation_started_at
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    if started_at < timeout_threshold:
                        status = 'timeout'
                
                if status in status_counts:
                    status_counts[status] += 1
                elif status == 'timeout':
                    status_counts['error'] += 1
                
                submission_statuses.append({
                    'file_submission_id': sub.id,
                    'group_code': sub.group_code,
                    'file_name': sub.file_name,
                    'status': status,
                    'error': sub.evaluation_error,
                    'started_at': sub.evaluation_started_at.isoformat() + 'Z' if sub.evaluation_started_at else None
                })
            
            # Determine overall status
            if status_counts['processing'] > 0 or status_counts['pending'] > 0:
                overall_status = 'in_progress'
            elif status_counts['error'] > 0:
                overall_status = 'completed_with_errors'
            elif status_counts['completed'] > 0:
                overall_status = 'completed'
            else:
                overall_status = 'idle'
            
            return {
                'overall_status': overall_status,
                'counts': status_counts,
                'submissions': submission_statuses
            }
        finally:
            db.close()
    
    @staticmethod
    def start_evaluation(
        activity_id: str,
        activity_moodle_id: str,
        file_submission_ids: List[str],
        evaluator_id: str
    ) -> Dict[str, Any]:
        """Start background evaluation for selected submissions
        
        This method:
        1. Checks for already processing submissions
        2. Marks selected submissions as 'pending'
        3. Returns immediately (actual processing happens in background)
        
        Args:
            activity_id: Activity ID
            activity_moodle_id: Moodle instance ID
            file_submission_ids: List of file submission IDs to evaluate
            evaluator_id: LAMB evaluator ID
            
        Returns:
            Dictionary with started evaluation info
        """
        db = get_db_session()
        try:
            # Get submissions and check their status
            submissions = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.id.in_(file_submission_ids),
                FileSubmissionDB.activity_id == activity_id
            ).all()
            
            if not submissions:
                return {
                    'success': False,
                    'message': 'No submissions found',
                    'queued': 0
                }
            
            already_processing = []
            to_queue = []
            
            for sub in submissions:
                # Check if already processing or pending
                if sub.evaluation_status in [STATUS_PENDING, STATUS_PROCESSING]:
                    # Check for timeout
                    if sub.evaluation_status == STATUS_PROCESSING and sub.evaluation_started_at:
                        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=EVALUATION_TIMEOUT_MINUTES)
                        started_at = sub.evaluation_started_at
                        if started_at.tzinfo is None:
                            started_at = started_at.replace(tzinfo=timezone.utc)
                        if started_at < timeout_threshold:
                            # Timed out, can be re-queued
                            to_queue.append(sub)
                        else:
                            already_processing.append(sub.id)
                    else:
                        already_processing.append(sub.id)
                else:
                    to_queue.append(sub)
            
            # Mark submissions as pending
            now = datetime.now(timezone.utc)
            for sub in to_queue:
                sub.evaluation_status = STATUS_PENDING
                sub.evaluation_started_at = now
                sub.evaluation_error = None
            
            db.commit()
            
            queued_ids = [sub.id for sub in to_queue]
            
            return {
                'success': True,
                'message': f'{len(queued_ids)} submissions queued for evaluation',
                'queued': len(queued_ids),
                'queued_ids': queued_ids,
                'already_processing': already_processing,
                'evaluator_id': evaluator_id
            }
        except Exception as e:
            db.rollback()
            logging.error(f"Error starting evaluation: {e}")
            return {
                'success': False,
                'message': str(e),
                'queued': 0
            }
        finally:
            db.close()
    
    @staticmethod
    def process_evaluation_batch(
        activity_id: str,
        activity_moodle_id: str,
        file_submission_ids: List[str],
        evaluator_id: str,
        is_debug_mode: bool = False
    ) -> Dict[str, Any]:
        """Process a batch of evaluations (runs in background)
        
        This method is called from a background task to actually process the evaluations.
        
        Args:
            activity_id: Activity ID
            activity_moodle_id: Moodle instance ID
            file_submission_ids: List of file submission IDs to evaluate
            evaluator_id: LAMB evaluator ID
            is_debug_mode: Whether to collect debug information
            
        Returns:
            Dictionary with processing results
        """
        db = get_db_session()
        results = {
            'grades_created': 0,
            'grades_updated': 0,
            'errors': [],
            'debug_info': [] if is_debug_mode else None
        }
        
        try:
            for file_sub_id in file_submission_ids:
                try:
                    # Mark as processing
                    file_sub = db.query(FileSubmissionDB).filter(
                        FileSubmissionDB.id == file_sub_id
                    ).first()
                    
                    if not file_sub:
                        results['errors'].append({
                            'file_submission_id': file_sub_id,
                            'error': 'Submission not found'
                        })
                        continue
                    
                    file_sub.evaluation_status = STATUS_PROCESSING
                    file_sub.evaluation_started_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Extract text from file
                    try:
                        extracted_text = DocumentExtractor.extract_text_from_file(file_sub.file_path)
                    except Exception as e:
                        file_sub.evaluation_status = STATUS_ERROR
                        file_sub.evaluation_error = f"Error extracting text: {str(e)}"
                        db.commit()
                        results['errors'].append({
                            'file_submission_id': file_sub_id,
                            'error': f"Text extraction failed: {str(e)}"
                        })
                        continue
                    
                    # Call LAMB API
                    try:
                        logging.info(f"=== CALLING LAMB API ===")
                        logging.info(f"Evaluator ID: {evaluator_id}")
                        logging.info(f"Text length: {len(extracted_text)} chars")
                        logging.info(f"Text preview: {extracted_text[:200]}...")
                        
                        lamb_response = LAMBAPIService.evaluate_text(
                            text=extracted_text,
                            evaluator_id=evaluator_id
                        )
                        
                        logging.info(f"=== LAMB API RESPONSE ===")
                        logging.info(f"Response: {lamb_response}")
                    except Exception as e:
                        logging.error(f"LAMB API Exception: {type(e).__name__}: {str(e)}")
                        file_sub.evaluation_status = STATUS_ERROR
                        file_sub.evaluation_error = f"LAMB API error: {str(e)}"
                        db.commit()
                        results['errors'].append({
                            'file_submission_id': file_sub_id,
                            'error': f"LAMB API error: {str(e)}"
                        })
                        continue
                    
                    # Parse response
                    logging.info(f"=== PARSING RESPONSE ===")
                    parsed = LAMBAPIService.parse_evaluation_response(lamb_response)
                    logging.info(f"Parsed result: {parsed}")
                    
                    if is_debug_mode:
                        results['debug_info'].append({
                            'file_submission_id': file_sub_id,
                            'group_code': file_sub.group_code,
                            'extracted_text': extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text,
                            'lamb_raw_response': lamb_response,
                            'parsed_response': parsed,
                            'json_validation': parsed.get('json_validation', {})
                        })
                    
                    if not parsed.get('success'):
                        file_sub.evaluation_status = STATUS_ERROR
                        file_sub.evaluation_error = f"Failed to parse response: {parsed.get('error', 'Unknown error')}"
                        db.commit()
                        results['errors'].append({
                            'file_submission_id': file_sub_id,
                            'error': parsed.get('error', 'Failed to parse LAMB response')
                        })
                        continue
                    
                    # Get score and comment from parsed response
                    score = parsed.get('score')
                    comment = parsed.get('comment', '') or ''
                    
                    # If no score was extracted, treat as error
                    if score is None:
                        logging.warning(f"No score found in LAMB response for submission {file_sub_id}")
                        logging.warning(f"Raw response: {parsed.get('raw_response', 'N/A')}")
                        file_sub.evaluation_status = STATUS_ERROR
                        file_sub.evaluation_error = "LAMB response did not contain a valid score (expected 'NOTA FINAL: X.X' or 'FINAL SCORE: X.X')"
                        db.commit()
                        results['errors'].append({
                            'file_submission_id': file_sub_id,
                            'error': f"No score in LAMB response. Comment received: {comment[:200] if comment else 'None'}..."
                        })
                        continue
                    
                    existing_grade = db.query(GradeDB).filter(
                        GradeDB.file_submission_id == file_sub_id
                    ).first()
                    
                    if existing_grade:
                        existing_grade.score = score
                        existing_grade.comment = comment
                        existing_grade.created_at = datetime.now(timezone.utc)
                        results['grades_updated'] += 1
                    else:
                        new_grade = GradeDB(
                            id=str(uuid.uuid4()),
                            file_submission_id=file_sub_id,
                            score=score,
                            comment=comment,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.add(new_grade)
                        results['grades_created'] += 1
                    
                    # Mark as completed
                    file_sub.evaluation_status = STATUS_COMPLETED
                    file_sub.evaluation_error = None
                    db.commit()
                    
                except Exception as e:
                    db.rollback()
                    logging.error(f"Error processing submission {file_sub_id}: {e}")
                    
                    # Try to mark as error
                    try:
                        file_sub = db.query(FileSubmissionDB).filter(
                            FileSubmissionDB.id == file_sub_id
                        ).first()
                        if file_sub:
                            file_sub.evaluation_status = STATUS_ERROR
                            file_sub.evaluation_error = str(e)
                            db.commit()
                    except:
                        pass
                    
                    results['errors'].append({
                        'file_submission_id': file_sub_id,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logging.error(f"Error in batch evaluation: {e}")
            return {
                'grades_created': results['grades_created'],
                'grades_updated': results['grades_updated'],
                'errors': results['errors'] + [{'error': str(e)}],
                'debug_info': results['debug_info']
            }
        finally:
            db.close()
    
    @staticmethod
    def reset_stuck_evaluations(activity_id: str, activity_moodle_id: str) -> int:
        """Reset evaluations that have been stuck in processing for too long
        
        Args:
            activity_id: Activity ID
            activity_moodle_id: Moodle instance ID
            
        Returns:
            Number of evaluations reset
        """
        db = get_db_session()
        try:
            timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=EVALUATION_TIMEOUT_MINUTES)
            
            stuck = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.activity_id == activity_id,
                FileSubmissionDB.activity_moodle_id == activity_moodle_id,
                FileSubmissionDB.evaluation_status == STATUS_PROCESSING,
                FileSubmissionDB.evaluation_started_at < timeout_threshold
            ).all()
            
            count = 0
            for sub in stuck:
                sub.evaluation_status = STATUS_ERROR
                sub.evaluation_error = 'Evaluation timed out'
                count += 1
            
            db.commit()
            return count
        except Exception as e:
            db.rollback()
            logging.error(f"Error resetting stuck evaluations: {e}")
            return 0
        finally:
            db.close()
    
    @staticmethod
    def clear_evaluation_status(file_submission_ids: List[str]) -> int:
        """Clear evaluation status for specific submissions (allow re-evaluation)
        
        Args:
            file_submission_ids: List of file submission IDs
            
        Returns:
            Number of submissions cleared
        """
        db = get_db_session()
        try:
            count = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.id.in_(file_submission_ids)
            ).update({
                FileSubmissionDB.evaluation_status: None,
                FileSubmissionDB.evaluation_started_at: None,
                FileSubmissionDB.evaluation_error: None
            }, synchronize_session=False)
            
            db.commit()
            return count
        except Exception as e:
            db.rollback()
            logging.error(f"Error clearing evaluation status: {e}")
            return 0
        finally:
            db.close()
