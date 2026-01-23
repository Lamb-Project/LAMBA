import uuid
import secrets
import string
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import (
    Activity, ActivityCreate, ActivityUpdate, ActivityType, 
    FileSubmission, StudentSubmission, OptimizedSubmissionView,
    StudentActivityView, Grade
)
from db_models import (
    ActivityDB, FileSubmissionDB, StudentSubmissionDB, UserDB
)
from database import get_db_session
from grade_service import GradeService
from storage_service import FileStorageService

class ActivitiesService:
    """
    Optimized activities service that uses the new storage structure.
    Eliminates data duplication and separates concerns properly.
    """
    
    @staticmethod
    def create_activity(activity_data: ActivityCreate, user_id: str, course_id: str, course_moodle_id: str, activity_id: Optional[str] = None) -> Activity:
        """Create a new activity
        
        Args:
            activity_data: Activity creation data
            user_id: User ID creating the activity
            course_id: Course ID from LTI (context_id)
            course_moodle_id: Moodle instance ID (part of course composite key)
            activity_id: Optional activity ID (uses resource_link_id from LTI)
        """
        # Validate activity type
        if activity_data.activity_type not in [ActivityType.INDIVIDUAL, ActivityType.GROUP]:
            raise ValueError("Invalid activity type. Must be 'individual' or 'group'")
        
        # Validate group size for group activities
        if activity_data.activity_type == ActivityType.GROUP:
            if not activity_data.max_group_size or activity_data.max_group_size < 2:
                raise ValueError("Group activities must have a maximum group size of at least 2")
        else:
            # For individual activities, max_group_size should be None
            activity_data.max_group_size = None
        
        # Validate deadline is not in the past
        if activity_data.deadline:
            # Normalize both dates to naive UTC datetimes for proper comparison
            deadline_naive = activity_data.deadline.replace(tzinfo=None) if activity_data.deadline.tzinfo else activity_data.deadline
            now_naive = datetime.now(timezone.utc)
        
        db = get_db_session()
        try:
            # Create activity
            if not activity_id:
                activity_id = str(uuid.uuid4())
            
            # Check if activity with same composite ID already exists
            existing_activity_by_id = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == course_moodle_id
            ).first()
            if existing_activity_by_id:
                raise ValueError(f"Ya existe una actividad con el ID '{activity_id}' en esta instancia de Moodle")
            
            # Ensure filesystem structure exists for this activity
            FileStorageService.ensure_activity_directory(course_moodle_id, course_id, activity_id)

            db_activity = ActivityDB(
                id=activity_id,
                title=activity_data.title.strip(),
                description=activity_data.description.strip(),
                activity_type=activity_data.activity_type,
                max_group_size=activity_data.max_group_size,
                creator_id=user_id,
                creator_moodle_id=course_moodle_id,  # Same as course_moodle_id (activity's moodle)
                created_at=datetime.now(timezone.utc),
                course_id=course_id,
                course_moodle_id=course_moodle_id,
                deadline=activity_data.deadline,
                evaluator_id=activity_data.evaluator_id.strip() if activity_data.evaluator_id else None
            )
            
            db.add(db_activity)
            db.commit()
            db.refresh(db_activity)
            
            return Activity(
                id=db_activity.id,
                title=db_activity.title,
                description=db_activity.description,
                activity_type=db_activity.activity_type,
                max_group_size=db_activity.max_group_size,
                creator_id=db_activity.creator_id,
                creator_moodle_id=db_activity.creator_moodle_id,
                created_at=db_activity.created_at,
                course_id=db_activity.course_id,
                course_moodle_id=db_activity.course_moodle_id,
                deadline=db_activity.deadline,
                evaluator_id=db_activity.evaluator_id
            )
        finally:
            db.close()
    
    @staticmethod
    def create_submission(activity_id: str, student_id: str, student_name: str, 
                         student_email: Optional[str], file_name: str, file_content: bytes, 
                         file_size: int, file_type: str, course_id: str, course_moodle_id: str,
                         student_moodle_id: str, lis_result_sourcedid: Optional[str] = None) -> OptimizedSubmissionView:
        """Create a new submission using the optimized storage structure
        
        Args:
            activity_id: Activity ID
            student_id: Student ID
            student_name: Student name
            student_email: Student email
            file_name: File name
            file_content: File content bytes
            file_size: File size
            file_type: File MIME type
            course_id: Course ID from LTI (context_id)
            course_moodle_id: Moodle instance ID (part of course composite key)
            student_moodle_id: Student's Moodle instance ID (for composite key)
            lis_result_sourcedid: LIS result sourcedid for grade passback
        """
        db = get_db_session()
        try:
            # Check if activity exists (using composite key - activity_moodle_id = course_moodle_id)
            activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == course_moodle_id
            ).first()
            if not activity:
                raise ValueError("Activity not found")

            # Always rely on the actual content length
            file_size = len(file_content)
            
            # Check if student already has a submission for this activity
            existing_student_submission = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.activity_id == activity_id,
                StudentSubmissionDB.activity_moodle_id == course_moodle_id,
                StudentSubmissionDB.student_id == student_id,
                StudentSubmissionDB.student_moodle_id == student_moodle_id
            ).first()
            
            if existing_student_submission:
                # Update existing submission
                file_submission = db.query(FileSubmissionDB).filter(
                    FileSubmissionDB.id == existing_student_submission.file_submission_id
                ).first()
                
                if file_submission and file_submission.uploaded_by == student_id:
                    # Student owns the file - update it and replace file on disk
                    relative_path = FileStorageService.save_submission_file(
                        moodle_id=course_moodle_id,
                        course_id=course_id,
                        activity_id=activity_id,
                        submission_id=file_submission.id,
                        file_name=file_name,
                        file_bytes=file_content,
                        previous_file_path=file_submission.file_path
                    )
                    file_submission.file_name = file_name
                    file_submission.file_path = relative_path
                    file_submission.file_size = file_size
                    file_submission.file_type = file_type
                    file_submission.uploaded_at = datetime.now(timezone.utc)
                
                # Update student submission LTI data
                if lis_result_sourcedid:
                    existing_student_submission.lis_result_sourcedid = lis_result_sourcedid
                existing_student_submission.joined_at = datetime.now(timezone.utc)
                
                db.commit()
                
                # Return API response model
                # For existing submissions, student is not considered group leader in update
                is_group_leader = False
                group_code_uses = None
                grade = GradeService.get_grade_by_file_submission(file_submission.id)
                return ActivitiesService._create_submission_view(
                    file_submission, existing_student_submission, student_name, student_email, is_group_leader, group_code_uses, grade
                )
            
            # Create new submission
            file_submission_id = str(uuid.uuid4())
            student_submission_id = str(uuid.uuid4())
            
            # Determine group settings for group activities
            group_code = None
            max_group_members = 1
            is_group_leader = False
            
            if activity.activity_type == ActivityType.GROUP:
                group_code = ActivitiesService._generate_group_code(db)
                max_group_members = activity.max_group_size
                is_group_leader = True
            
            # Persist file and create file submission (one per group/individual)
            relative_path = FileStorageService.save_submission_file(
                moodle_id=course_moodle_id,
                course_id=course_id,
                activity_id=activity_id,
                submission_id=file_submission_id,
                file_name=file_name,
                file_bytes=file_content
            )

            db_file_submission = FileSubmissionDB(
                id=file_submission_id,
                activity_id=activity_id,
                activity_moodle_id=course_moodle_id,
                file_name=file_name,
                file_path=relative_path,
                file_size=file_size,
                file_type=file_type,
                uploaded_at=datetime.now(timezone.utc),
                uploaded_by=student_id,
                uploaded_by_moodle_id=course_moodle_id,
                group_code=group_code,
                max_group_members=max_group_members
            )
            
            # Create student submission (one per student)
            db_student_submission = StudentSubmissionDB(
                id=student_submission_id,
                file_submission_id=file_submission_id,
                student_id=student_id,
                student_moodle_id=student_moodle_id,
                activity_id=activity_id,
                activity_moodle_id=course_moodle_id,
                lis_result_sourcedid=lis_result_sourcedid,
                joined_at=datetime.now(timezone.utc)
            )
            
            db.add(db_file_submission)
            db.add(db_student_submission)
            db.commit()
            db.refresh(db_file_submission)
            db.refresh(db_student_submission)
            
            # Note: Automatic grade creation has been removed
            # Grades will now be created manually via the "Automatic Evaluation" button
            
            # Return API response model
            # For new submissions, group_code_uses starts at 0 if it's a group submission
            group_code_uses = 0 if is_group_leader and group_code else None
            grade = GradeService.get_grade_by_file_submission(db_file_submission.id)
            return ActivitiesService._create_submission_view(
                db_file_submission, db_student_submission, student_name, student_email, is_group_leader, group_code_uses, grade
            )
        finally:
            db.close()
    
    @staticmethod
    def submit_with_group_code(activity_id: str, group_code: str, student_id: str, 
                              student_name: str, student_email: Optional[str], course_id: str,
                              course_moodle_id: str, lis_result_sourcedid: Optional[str] = None) -> OptimizedSubmissionView:
        """Submit using a group code for group activities
        
        Args:
            activity_id: Activity ID
            group_code: Group code to join
            student_id: Student ID
            student_name: Student name
            student_email: Student email
            course_id: Course ID from LTI (context_id)
            course_moodle_id: Moodle instance ID (part of course composite key)
            lis_result_sourcedid: LIS result sourcedid for grade passback
        """
        db = get_db_session()
        try:
            # Check if activity exists (using composite key - activity_moodle_id = course_moodle_id)
            activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == course_moodle_id
            ).first()
            if not activity:
                raise ValueError("Activity not found")
            
            # Check if activity is a group activity
            if activity.activity_type != ActivityType.GROUP:
                raise ValueError("Group codes can only be used for group activities")
            
            # Find file submission with this group code
            file_submission = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.group_code == group_code,
                FileSubmissionDB.activity_id == activity_id
            ).first()
            
            if not file_submission:
                raise ValueError("Invalid group code")
            
            # Check if group has reached maximum capacity
            current_members = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.file_submission_id == file_submission.id
            ).count()
            
            if current_members >= file_submission.max_group_members:
                raise ValueError("Group code has reached maximum number of uses")
            
            # Check if student already has a submission for this activity
            existing_student_submission = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.activity_id == activity_id,
                StudentSubmissionDB.activity_moodle_id == course_moodle_id,
                StudentSubmissionDB.student_id == student_id,
                StudentSubmissionDB.student_moodle_id == course_moodle_id
            ).first()
            
            if existing_student_submission:
                if existing_student_submission.file_submission_id == file_submission.id:
                    # Already in this group - error
                    raise ValueError("Ya eres miembro de este grupo")
                else:
                    raise ValueError("You have already submitted to this activity")
            
            # Create new student submission for this group
            student_submission_id = str(uuid.uuid4())
            db_student_submission = StudentSubmissionDB(
                id=student_submission_id,
                file_submission_id=file_submission.id,
                student_id=student_id,
                student_moodle_id=course_moodle_id,
                activity_id=activity_id,
                activity_moodle_id=course_moodle_id,
                lis_result_sourcedid=lis_result_sourcedid,
                joined_at=datetime.now(timezone.utc)
            )
            
            db.add(db_student_submission)
            db.commit()
            db.refresh(db_student_submission)
            
            # Note: No need to create evaluation here as it already exists for the file_submission
            
            # Return API response model
            grade = GradeService.get_grade_by_file_submission(file_submission.id)
            return ActivitiesService._create_submission_view(
                file_submission, db_student_submission, student_name, student_email, False, None, grade
            )
        finally:
            db.close()
    
    @staticmethod
    def get_student_submission(activity_id: str, activity_moodle_id: str, student_id: str, student_moodle_id: str) -> Optional[OptimizedSubmissionView]:
        """Get student's submission for a specific activity - optimized version with composite keys
        
        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
            student_id: Student ID
            student_moodle_id: Student's Moodle instance ID
        """
        db = get_db_session()
        try:
            # Find student submission (using composite keys)
            student_submission = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.activity_id == activity_id,
                StudentSubmissionDB.activity_moodle_id == activity_moodle_id,
                StudentSubmissionDB.student_id == student_id,
                StudentSubmissionDB.student_moodle_id == student_moodle_id
            ).first()
            
            if not student_submission:
                return None
            
            # Get associated file submission
            file_submission = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.id == student_submission.file_submission_id
            ).first()
            
            if not file_submission:
                return None
            
            # Get user data (using composite key)
            user = db.query(UserDB).filter(
                UserDB.id == student_id,
                UserDB.moodle_id == student_moodle_id
            ).first()
            student_name = user.full_name if user else ""
            student_email = user.email if user else ""
            
            # Determine if this student is the group leader
            is_group_leader = (file_submission.uploaded_by == student_id and file_submission.group_code is not None)
            
            # Calculate group code uses if it's a group submission
            group_code_uses = None
            if file_submission.group_code:
                group_uses_count = db.query(StudentSubmissionDB).filter(
                    StudentSubmissionDB.file_submission_id == file_submission.id
                ).count()
                group_code_uses = group_uses_count - 1 if is_group_leader else 0
            
            grade = GradeService.get_grade_by_file_submission(file_submission.id)
            return ActivitiesService._create_submission_view(
                file_submission, student_submission, student_name, student_email, is_group_leader, group_code_uses, grade
            )
        finally:
            db.close()
    
    @staticmethod
    def get_submissions_by_activity(activity_id: str, activity_moodle_id: str) -> Dict[str, Any]:
        """Get all submissions for a specific activity organized by type (individual/group)
        
        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
        """
        db = get_db_session()
        try:
            # Get activity to check type (using composite key)
            activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == activity_moodle_id
            ).first()
            if not activity:
                raise ValueError("Activity not found")
            
            # Get all student submissions for this activity (using composite key)
            student_submissions = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.activity_id == activity_id,
                StudentSubmissionDB.activity_moodle_id == activity_moodle_id
            ).all()
            
            submissions_list = []
            groups_dict = {}
            
            for student_submission in student_submissions:
                # Get associated file submission
                file_submission = db.query(FileSubmissionDB).filter(
                    FileSubmissionDB.id == student_submission.file_submission_id
                ).first()
                
                if not file_submission:
                    continue
                
                # Get user data (using composite key)
                user = db.query(UserDB).filter(
                    UserDB.id == student_submission.student_id,
                    UserDB.moodle_id == student_submission.student_moodle_id
                ).first()
                student_name = user.full_name if user else ""
                student_email = user.email if user else ""
                
                # Determine if this student is the group leader
                is_group_leader = (file_submission.uploaded_by == student_submission.student_id and file_submission.group_code is not None)
                
                # Calculate group code uses for this submission
                group_code_uses = None
                if file_submission.group_code and is_group_leader:
                    group_uses_count = len([ss for ss in student_submissions if ss.file_submission_id == file_submission.id])
                    group_code_uses = group_uses_count - 1
                
                # Get grade for this file submission
                grade = GradeService.get_grade_by_file_submission(file_submission.id)
                
                submission_view = ActivitiesService._create_submission_view(
                    file_submission, student_submission, student_name, student_email, is_group_leader, group_code_uses, grade
                )
                
                submissions_list.append(submission_view)
                
                # If it's a group submission, organize by group
                if file_submission.group_code:
                    if file_submission.group_code not in groups_dict:
                        # Convert Grade Pydantic model to dict for proper JSON serialization
                        grade_dict = None
                        if grade:
                            grade_dict = {
                                'id': grade.id,
                                'file_submission_id': grade.file_submission_id,
                                'score': grade.score,
                                'comment': grade.comment,
                                'created_at': grade.created_at.isoformat() + 'Z' if grade.created_at else None
                            }
                        groups_dict[file_submission.group_code] = {
                            'group_code': file_submission.group_code,
                            'file_submission': submission_view.file_submission,
                            'members': [],
                            'group_leader': None,
                            'grade': grade_dict  # Add grade at group level (as dict)
                        }
                    
                    member_info = {
                        'student_id': student_submission.student_id,
                        'student_name': student_name,
                        'student_email': student_email,
                        'joined_at': student_submission.joined_at,
                        'is_group_leader': is_group_leader
                    }
                    
                    groups_dict[file_submission.group_code]['members'].append(member_info)
                    
                    if is_group_leader:
                        groups_dict[file_submission.group_code]['group_leader'] = member_info
            
            # Organize final result
            if activity.activity_type == ActivityType.GROUP:
                groups = list(groups_dict.values())
                return {
                    'activity': Activity(
                        id=activity.id,
                        title=activity.title,
                        description=activity.description,
                        activity_type=activity.activity_type,
                        max_group_size=activity.max_group_size,
                        creator_id=activity.creator_id,
                        creator_moodle_id=activity.creator_moodle_id,
                        created_at=activity.created_at,
                        course_id=activity.course_id,
                        course_moodle_id=activity.course_moodle_id,
                        deadline=activity.deadline,
                        evaluator_id=activity.evaluator_id
                    ),
                    'activity_type': 'group',
                    'total_submissions': len(groups),
                    'groups': groups
                }
            else:
                # Individual submissions
                individual_submissions = [s for s in submissions_list if not s.file_submission.group_code]
                return {
                    'activity': Activity(
                        id=activity.id,
                        title=activity.title,
                        description=activity.description,
                        activity_type=activity.activity_type,
                        max_group_size=activity.max_group_size,
                        creator_id=activity.creator_id,
                        creator_moodle_id=activity.creator_moodle_id,
                        created_at=activity.created_at,
                        course_id=activity.course_id,
                        course_moodle_id=activity.course_moodle_id,
                        deadline=activity.deadline,
                        evaluator_id=activity.evaluator_id
                    ),
                    'activity_type': 'individual',
                    'total_submissions': len(individual_submissions),
                    'submissions': individual_submissions
                }
        finally:
            db.close()
    
    @staticmethod
    def get_group_members(activity_id: str, activity_moodle_id: str, group_code: str) -> List[OptimizedSubmissionView]:
        """Get all members of a group by group code - optimized version with composite keys
        
        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
            group_code: Group code
        """
        db = get_db_session()
        try:
            # Find file submission with this group code (using composite key)
            file_submission = db.query(FileSubmissionDB).filter(
                FileSubmissionDB.group_code == group_code,
                FileSubmissionDB.activity_id == activity_id,
                FileSubmissionDB.activity_moodle_id == activity_moodle_id
            ).first()
            
            if not file_submission:
                return []
            
            # Get all student submissions for this file
            student_submissions = db.query(StudentSubmissionDB).filter(
                StudentSubmissionDB.file_submission_id == file_submission.id
            ).all()
            
            result = []
            for student_submission in student_submissions:
                # Get user data (using composite key)
                user = db.query(UserDB).filter(
                    UserDB.id == student_submission.student_id,
                    UserDB.moodle_id == student_submission.student_moodle_id
                ).first()
                student_name = user.full_name if user else ""
                student_email = user.email if user else ""
                
                # Determine if this student is the group leader
                is_group_leader = (file_submission.uploaded_by == student_submission.student_id)
                
                # Calculate group code uses for legacy compatibility
                group_code_uses = len(student_submissions) - 1 if is_group_leader else 0
                
                grade = GradeService.get_grade_by_file_submission(file_submission.id)
                result.append(ActivitiesService._create_submission_view(
                    file_submission, student_submission, student_name, student_email, 
                    is_group_leader, group_code_uses, grade
                ))
            
            return result
        finally:
            db.close()
    
    @staticmethod
    def get_student_activity_view_by_id(resource_link_id: str, moodle_id: str, student_id: str, student_moodle_id: str) -> StudentActivityView:
        """Get student view of activity based on resource_link_id (activity ID) and moodle_id
        
        Args:
            resource_link_id: Activity ID from LTI (resource_link_id)
            moodle_id: Moodle instance ID
            student_id: Student user ID
            student_moodle_id: Student's Moodle instance ID
        """
        # Find activity by composite ID
        activity = ActivitiesService.get_activity_by_id(resource_link_id, moodle_id)
        
        if not activity:
            return StudentActivityView(
                activity=None,
                student_submission=None,
                can_submit=False
            )
        
        # Get student's submission if exists (using composite keys)
        student_submission = ActivitiesService.get_student_submission(activity.id, moodle_id, student_id, student_moodle_id)
        
        return StudentActivityView(
            activity=activity,
            student_submission=student_submission,
            can_submit=True
        )
    

    
    @staticmethod
    def _generate_group_code(db: Session) -> str:
        """Generate a unique 8-character group code"""
        while True:
            # Generate a random 8-character code with uppercase letters and numbers
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            # Ensure it's unique by checking if any file submission already uses this code
            existing = db.query(FileSubmissionDB).filter(FileSubmissionDB.group_code == code).first()
            if not existing:
                return code
    
    # Unchanged methods from original service
    @staticmethod
    def get_activities_by_course(course_id: str) -> List[Activity]:
        """Get all activities for a specific course - unchanged"""
        db = get_db_session()
        try:
            db_activities = db.query(ActivityDB).filter(ActivityDB.course_id == course_id).all()
            return [
                Activity(
                    id=activity.id,
                    title=activity.title,
                    description=activity.description,
                    activity_type=activity.activity_type,
                    max_group_size=activity.max_group_size,
                    creator_id=activity.creator_id,
                    creator_moodle_id=activity.creator_moodle_id,
                    created_at=activity.created_at,
                    course_id=activity.course_id,
                    course_moodle_id=activity.course_moodle_id,
                    deadline=activity.deadline,
                    evaluator_id=activity.evaluator_id
                ) for activity in db_activities
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_activity_by_id(activity_id: str, moodle_id: str) -> Optional[Activity]:
        """Get a specific activity by composite ID (activity_id + moodle_id)
        
        Args:
            activity_id: Activity ID from LTI (resource_link_id)
            moodle_id: Moodle instance ID
        """
        db = get_db_session()
        try:
            db_activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == moodle_id
            ).first()
            if not db_activity:
                return None
            
            return Activity(
                id=db_activity.id,
                title=db_activity.title,
                description=db_activity.description,
                activity_type=db_activity.activity_type,
                max_group_size=db_activity.max_group_size,
                creator_id=db_activity.creator_id,
                creator_moodle_id=db_activity.creator_moodle_id,
                created_at=db_activity.created_at,
                course_id=db_activity.course_id,
                course_moodle_id=db_activity.course_moodle_id,
                deadline=db_activity.deadline,
                evaluator_id=db_activity.evaluator_id
            )
        finally:
            db.close()
    
    @staticmethod
    def get_activity_by_title_and_course(title: str, course_id: str) -> Optional[Activity]:
        """Get activity by title and course - unchanged"""
        db = get_db_session()
        try:
            db_activity = db.query(ActivityDB).filter(
                ActivityDB.title == title,
                ActivityDB.course_id == course_id
            ).first()
            
            if not db_activity:
                return None
            
            return Activity(
                id=db_activity.id,
                title=db_activity.title,
                description=db_activity.description,
                activity_type=db_activity.activity_type,
                max_group_size=db_activity.max_group_size,
                creator_id=db_activity.creator_id,
                creator_moodle_id=db_activity.creator_moodle_id,
                created_at=db_activity.created_at,
                course_id=db_activity.course_id,
                course_moodle_id=db_activity.course_moodle_id,
                deadline=db_activity.deadline,
                evaluator_id=db_activity.evaluator_id
            )
        finally:
            db.close()
    
    
    @staticmethod
    def get_activities_count() -> int:
        """Get total number of activities - unchanged"""
        db = get_db_session()
        try:
            return db.query(ActivityDB).count()
        finally:
            db.close()
    
    @staticmethod
    def _create_submission_view(
        file_submission: FileSubmissionDB, 
        student_submission: StudentSubmissionDB, 
        student_name: str, 
        student_email: Optional[str],
        is_group_leader: bool = False,
        group_code_uses: Optional[int] = None,
        grade: Optional['Grade'] = None
    ) -> OptimizedSubmissionView:
        """Convert database objects to API response model"""
        
        # Create FileSubmission model
        file_sub_model = FileSubmission(
            id=file_submission.id,
            activity_id=file_submission.activity_id,
            activity_moodle_id=file_submission.activity_moodle_id,
            file_name=file_submission.file_name,
            file_path=file_submission.file_path,
            file_size=file_submission.file_size,
            file_type=file_submission.file_type,
            uploaded_at=file_submission.uploaded_at,
            uploaded_by=file_submission.uploaded_by,
            uploaded_by_moodle_id=file_submission.uploaded_by_moodle_id,
            group_code=file_submission.group_code,
            max_group_members=file_submission.max_group_members
        )
        
        # Create StudentSubmission model
        student_sub_model = StudentSubmission(
            id=student_submission.id,
            file_submission_id=student_submission.file_submission_id,
            student_id=student_submission.student_id,
            student_moodle_id=student_submission.student_moodle_id,
            activity_id=student_submission.activity_id,
            activity_moodle_id=student_submission.activity_moodle_id,
            lis_result_sourcedid=student_submission.lis_result_sourcedid,
            joined_at=student_submission.joined_at,
            sent_to_moodle=student_submission.sent_to_moodle,
            sent_to_moodle_at=student_submission.sent_to_moodle_at
        )
        
        # Create OptimizedSubmissionView
        return OptimizedSubmissionView(
            file_submission=file_sub_model,
            student_submission=student_sub_model,
            student_name=student_name,
            student_email=student_email,
            is_group_leader=is_group_leader,
            group_code_uses=group_code_uses,
            grade=grade
        )
    
    @staticmethod
    def update_activity(activity_id: str, activity_moodle_id: str, activity_data: ActivityUpdate, 
                       user_id: str, user_moodle_id: str, course_id: str = None) -> Activity:
        """Update an existing activity's description, deadline, and/or evaluator
        
        Only teachers from the same course can update the activity.
        
        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
            activity_data: Updated activity data
            user_id: User ID (for potential future logging/auditing)
            user_moodle_id: User's Moodle instance ID (for potential future logging/auditing)
            course_id: Course ID from LTI session to verify access
        """
        db = get_db_session()
        try:
            # Get the activity (using composite key)
            db_activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == activity_moodle_id
            ).first()
            if not db_activity:
                raise ValueError("Actividad no encontrada")
            
            # Verify the user is accessing from the same course
            if course_id and db_activity.course_id != course_id:
                raise ValueError("No tienes permisos para actualizar esta actividad desde este curso")
            
            # Update the description if provided
            if activity_data.description is not None:
                db_activity.description = activity_data.description.strip()
            
            # Update the deadline if provided
            if activity_data.deadline is not None:
                # Validate deadline is not in the past
                # Normalize both dates to naive UTC datetimes for proper comparison
                deadline_naive = activity_data.deadline.replace(tzinfo=None) if activity_data.deadline.tzinfo else activity_data.deadline
                now_naive = datetime.now(timezone.utc)
                
                if deadline_naive < now_naive:
                    raise ValueError("La fecha límite no puede ser anterior a la fecha y hora actual")
                db_activity.deadline = activity_data.deadline
            
            # Update evaluator_id if provided
            if activity_data.evaluator_id is not None:
                db_activity.evaluator_id = activity_data.evaluator_id.strip() if activity_data.evaluator_id else None
            
            db.commit()
            db.refresh(db_activity)
            
            return Activity(
                id=db_activity.id,
                title=db_activity.title,
                description=db_activity.description,
                activity_type=db_activity.activity_type,
                max_group_size=db_activity.max_group_size,
                creator_id=db_activity.creator_id,
                creator_moodle_id=db_activity.creator_moodle_id,
                created_at=db_activity.created_at,
                course_id=db_activity.course_id,
                course_moodle_id=db_activity.course_moodle_id,
                deadline=db_activity.deadline,
                evaluator_id=db_activity.evaluator_id
            )
        finally:
            db.close()