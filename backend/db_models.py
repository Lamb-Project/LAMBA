from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class MoodleDB(Base):
    __tablename__ = "moodle_instances"
    
    id = Column(String, primary_key=True, index=True)  # Moodle instance ID from LTI (tool_consumer_instance_guid)
    name = Column(String, nullable=False)  # Moodle instance name from LTI (tool_consumer_instance_name)
    lis_outcome_service_url = Column(String, nullable=True)  # LTI outcome service URL
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = relationship("CourseDB", back_populates="moodle_instance")
    users = relationship("UserDB", back_populates="moodle_instance")

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)  # User ID from LTI
    moodle_id = Column(String, ForeignKey("moodle_instances.id"), primary_key=True, nullable=False)  # Moodle instance ID
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False)  # "student" or "teacher"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    moodle_instance = relationship("MoodleDB", back_populates="users")
    created_activities = relationship("ActivityDB", back_populates="creator")
    student_submissions = relationship("StudentSubmissionDB", back_populates="student")

class CourseDB(Base):
    __tablename__ = "courses"
    
    id = Column(String, primary_key=True)  # Course ID from LTI (context_id)
    moodle_id = Column(String, ForeignKey("moodle_instances.id"), primary_key=True, nullable=False)  # Moodle instance ID
    title = Column(String, nullable=False)  # Course title from LTI
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    moodle_instance = relationship("MoodleDB", back_populates="courses")
    activities = relationship("ActivityDB", back_populates="course")

class ActivityDB(Base):
    __tablename__ = "activities"
    
    id = Column(String, primary_key=True)  # Activity ID from LTI (resource_link_id)
    course_moodle_id = Column(String, primary_key=True, nullable=False)  # Moodle instance ID (also activity's moodle_id)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    activity_type = Column(String, nullable=False)  # "individual" or "group"
    max_group_size = Column(Integer, nullable=True)
    creator_id = Column(String, nullable=False)  # Creator user ID
    creator_moodle_id = Column(String, nullable=False)  # Creator's Moodle instance ID
    created_at = Column(DateTime, default=datetime.utcnow)
    course_id = Column(String, nullable=False)  # Course ID from LTI
    deadline = Column(DateTime, nullable=True)  # Fecha y hora límite de entrega
    evaluator_id = Column(String, nullable=True)  # ID del evaluador automático
    
    # Foreign key constraints for composite keys
    __table_args__ = (
        ForeignKeyConstraint(['course_id', 'course_moodle_id'], ['courses.id', 'courses.moodle_id']),
        ForeignKeyConstraint(['creator_id', 'creator_moodle_id'], ['users.id', 'users.moodle_id']),
    )
    
    # Relationships
    creator = relationship("UserDB", back_populates="created_activities", foreign_keys=[creator_id, creator_moodle_id])
    course = relationship("CourseDB", back_populates="activities", foreign_keys=[course_id, course_moodle_id])
    student_submissions = relationship("StudentSubmissionDB", back_populates="activity")

class FileSubmissionDB(Base):
    __tablename__ = "file_submissions"
    
    id = Column(String, primary_key=True, index=True)
    activity_id = Column(String, nullable=False, index=True)  # Activity ID from LTI (no FK, accessed via student_submissions)
    activity_moodle_id = Column(String, nullable=False, index=True)  # Moodle instance ID (no FK, accessed via student_submissions)
    
    # File information (unique per group/individual submission)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String, nullable=False)  # MIME type
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String, nullable=False)  # User ID who uploaded the file
    uploaded_by_moodle_id = Column(String, nullable=False)  # Uploader's Moodle instance ID
    
    # Group information
    group_code = Column(String, nullable=True)  # Unique code for group submissions
    max_group_members = Column(Integer, default=1)  # Max members allowed for this submission
    
    # Foreign key constraints for composite keys
    __table_args__ = (
        ForeignKeyConstraint(['uploaded_by', 'uploaded_by_moodle_id'], ['users.id', 'users.moodle_id']),
    )
    
    # Relationships
    student_submissions = relationship("StudentSubmissionDB", back_populates="file_submission")
    grade = relationship("GradeDB", back_populates="file_submission", uselist=False)

class StudentSubmissionDB(Base):
    __tablename__ = "student_submissions"
    
    id = Column(String, primary_key=True, index=True)
    file_submission_id = Column(String, ForeignKey("file_submissions.id"), nullable=False)
    student_id = Column(String, nullable=False)  # Student user ID
    student_moodle_id = Column(String, nullable=False)  # Student's Moodle instance ID
    activity_id = Column(String, nullable=False)  # Activity ID from LTI
    activity_moodle_id = Column(String, nullable=False)  # Moodle instance ID (for activity FK)
    
    # LTI-specific data (unique per student)
    lis_result_sourcedid = Column(String, nullable=True)  # Required for sending grades back to Moodle
    joined_at = Column(DateTime, default=datetime.utcnow)  # When this student joined the submission
    sent_to_moodle = Column(Boolean, default=False, nullable=False)  # Track if grade was sent to Moodle
    sent_to_moodle_at = Column(DateTime, nullable=True)  # When the grade was sent to Moodle
    
    # Unique constraint: one submission per student per activity (with moodle_id)
    __table_args__ = (
        UniqueConstraint('student_id', 'student_moodle_id', 'activity_id', 'activity_moodle_id', name='uq_student_activity_submission'),
        ForeignKeyConstraint(['activity_id', 'activity_moodle_id'], ['activities.id', 'activities.course_moodle_id']),
        ForeignKeyConstraint(['student_id', 'student_moodle_id'], ['users.id', 'users.moodle_id']),
    )
    
    # Relationships
    file_submission = relationship("FileSubmissionDB", back_populates="student_submissions")
    student = relationship("UserDB", back_populates="student_submissions", foreign_keys=[student_id, student_moodle_id])
    activity = relationship("ActivityDB", back_populates="student_submissions", foreign_keys=[activity_id, activity_moodle_id])

class GradeDB(Base):
    __tablename__ = "grades"
    
    id = Column(String, primary_key=True, index=True)
    file_submission_id = Column(String, ForeignKey("file_submissions.id"), nullable=False)
    score = Column(Float, nullable=False)  # Score 
    comment = Column(Text, nullable=True)  # Feedback comment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    file_submission = relationship("FileSubmissionDB", back_populates="grade")