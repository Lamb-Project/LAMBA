from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, field_serializer, field_validator

class UserRole:
    STUDENT = "student"
    TEACHER = "teacher"

class User(BaseModel):
    id: str  # User ID from LTI
    moodle_id: str  # Moodle instance ID (part of composite key)
    full_name: str
    email: Optional[str] = None
    role: str  # "student" or "teacher"
    created_at: Optional[datetime] = None
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class Moodle(BaseModel):
    id: str  # Moodle instance ID from LTI (tool_consumer_instance_guid)
    name: str  # Moodle instance name from LTI (tool_consumer_instance_name)
    lis_outcome_service_url: Optional[str] = None  # LTI outcome service URL
    created_at: Optional[datetime] = None
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class Course(BaseModel):
    id: str  # Course ID from LTI (context_id)
    title: str  # Course title from LTI (context_title)
    moodle_id: Optional[str] = None  # Moodle instance ID
    created_at: Optional[datetime] = None
    
    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class ActivityType:
    INDIVIDUAL = "individual"
    GROUP = "group"

class Activity(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    activity_type: Literal["individual", "group"]
    max_group_size: Optional[int] = None
    creator_id: str  # User ID from LTI
    creator_moodle_id: str  # Creator's Moodle instance ID
    created_at: Optional[datetime] = None
    course_id: str  # Course ID from LTI
    course_moodle_id: str  # Moodle instance ID (part of course composite key)
    deadline: Optional[datetime] = None  # Fecha y hora límite de entrega
    evaluator_id: Optional[str] = None  # ID del evaluador automático
    
    @field_serializer('created_at', 'deadline')
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class ActivityCreate(BaseModel):
    title: str
    description: str
    activity_type: Literal["individual", "group"]
    max_group_size: Optional[int] = None
    deadline: Optional[datetime] = None
    evaluator_id: Optional[str] = None
    
    @field_validator('activity_type', mode='before')
    @classmethod
    def normalize_activity_type(cls, v):
        """Normalize activity_type to lowercase for case-insensitive validation"""
        if isinstance(v, str):
            return v.lower()
        return v

class ActivityUpdate(BaseModel):
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    evaluator_id: Optional[str] = None

class ActivityResponse(BaseModel):
    success: bool
    message: str
    activity: Optional[Activity] = None

# Grade passback models
class Grade(BaseModel):
    id: str
    file_submission_id: str
    # AI proposed grade
    ai_score: Optional[float] = None  # AI proposed score (0-10)
    ai_comment: Optional[str] = None  # AI feedback
    ai_evaluated_at: Optional[datetime] = None
    # Final grade (from professor)
    score: Optional[float] = None  # Professor's final score (0-10)
    comment: Optional[str] = None  # Professor's feedback
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @field_serializer('created_at', 'updated_at', 'ai_evaluated_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

# Group submission model
class GroupCodeSubmission(BaseModel):
    activity_id: str
    group_code: str

# Optimized submission models
class FileSubmission(BaseModel):
    id: str
    activity_id: str
    activity_moodle_id: str  # Moodle instance ID (part of activity composite key)
    file_name: str
    file_path: str
    file_size: int
    file_type: str  # MIME type
    uploaded_at: Optional[datetime] = None
    uploaded_by: str  # User ID who uploaded the file
    uploaded_by_moodle_id: str  # Uploader's Moodle instance ID
    group_code: Optional[str] = None  # Unique code for group submissions
    max_group_members: int = 1  # Max members allowed for this submission
    # Evaluation status tracking
    evaluation_status: Optional[str] = None  # null, 'pending', 'processing', 'completed', 'error'
    evaluation_started_at: Optional[datetime] = None
    evaluation_error: Optional[str] = None
    
    @field_serializer('uploaded_at')
    def serialize_uploaded_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None
    
    @field_serializer('evaluation_started_at')
    def serialize_evaluation_started_at(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class StudentSubmission(BaseModel):
    id: str
    file_submission_id: str
    student_id: str
    student_moodle_id: str  # Student's Moodle instance ID
    activity_id: str
    activity_moodle_id: str  # Moodle instance ID (part of activity composite key)
    lis_result_sourcedid: Optional[str] = None  # Required for sending grades back to Moodle
    joined_at: Optional[datetime] = None  # When this student joined the submission
    sent_to_moodle: bool = False  # Track if grade was sent to Moodle
    sent_to_moodle_at: Optional[datetime] = None  # When the grade was sent to Moodle
    
    @field_serializer('joined_at', 'sent_to_moodle_at')
    def serialize_datetimes(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() + 'Z' if value else None

class OptimizedSubmissionView(BaseModel):
    """Combined view of file submission + student submission for API responses"""
    # File submission data
    file_submission: FileSubmission
    # Student-specific data
    student_submission: StudentSubmission
    # User data (fetched separately to avoid storing in submissions)
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    # Group-specific data
    is_group_leader: bool = False
    group_code_uses: Optional[int] = None
    # Grade data
    grade: Optional[Grade] = None

class GroupCodeResponse(BaseModel):
    success: bool
    message: str
    submission: Optional[OptimizedSubmissionView] = None

class StudentActivityView(BaseModel):
    activity: Optional[Activity] = None
    student_submission: Optional[OptimizedSubmissionView] = None
    can_submit: bool = True

class GradeRequest(BaseModel):
    file_submission_id: str
    score: float
    comment: Optional[str] = None

class GradeUpdate(BaseModel):
    score: float
    comment: Optional[str] = None

class GradeResponse(BaseModel):
    success: bool
    message: str
    grade: Optional[Grade] = None

# User response models
class UserResponse(BaseModel):
    success: bool
    message: str
    user: Optional[User] = None

# Course response models
class CourseResponse(BaseModel):
    success: bool
    message: str
    course: Optional[Course] = None

# Moodle response models
class MoodleResponse(BaseModel):
    success: bool
    message: str
    moodle: Optional[Moodle] = None

# Submission response model
class SubmissionResponse(BaseModel):
    success: bool
    message: str
    submission: Optional[OptimizedSubmissionView] = None