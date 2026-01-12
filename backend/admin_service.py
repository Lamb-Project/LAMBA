"""
Service for admin-related operations.
Provides data retrieval for all system entities: Moodle instances, courses, activities, users, submissions, and files.
"""

import os
from database import get_db_session
from db_models import (
    MoodleDB, UserDB, CourseDB, ActivityDB, 
    StudentSubmissionDB, FileSubmissionDB, GradeDB
)


class AdminService:
    """Service for admin operations"""
    
    @staticmethod
    def verify_admin_credentials(username: str, password: str) -> bool:
        """
        Verify admin credentials against environment variables
        
        Args:
            username: Username to verify
            password: Password to verify
            
        Returns:
            bool: True if credentials match, False otherwise
        """
        admin_username = os.getenv("ADMIN_USERNAME", "")
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        
        return username == admin_username and password == admin_password
    
    @staticmethod
    def get_all_moodle_instances():
        """Get all Moodle instances from database"""
        db = get_db_session()
        try:
            moodles = db.query(MoodleDB).all()
            return [
                {
                    "id": m.id,
                    "name": m.name,
                    "lis_outcome_service_url": m.lis_outcome_service_url,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in moodles
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_courses():
        """Get all courses from database"""
        db = get_db_session()
        try:
            courses = db.query(CourseDB).all()
            return [
                {
                    "id": c.id,
                    "moodle_id": c.moodle_id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in courses
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_activities():
        """Get all activities from database"""
        db = get_db_session()
        try:
            activities = db.query(ActivityDB).all()
            return [
                {
                    "id": a.id,
                    "course_moodle_id": a.course_moodle_id,
                    "title": a.title,
                    "description": a.description,
                    "activity_type": a.activity_type,
                    "max_group_size": a.max_group_size,
                    "creator_id": a.creator_id,
                    "creator_moodle_id": a.creator_moodle_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "course_id": a.course_id,
                    "deadline": a.deadline.isoformat() if a.deadline else None,
                    "evaluator_id": a.evaluator_id
                }
                for a in activities
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_users():
        """Get all users from database"""
        db = get_db_session()
        try:
            users = db.query(UserDB).all()
            return [
                {
                    "id": u.id,
                    "moodle_id": u.moodle_id,
                    "full_name": u.full_name,
                    "email": u.email,
                    "role": u.role,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_submissions():
        """Get all student submissions from database"""
        db = get_db_session()
        try:
            submissions = db.query(StudentSubmissionDB).all()
            return [
                {
                    "id": s.id,
                    "file_submission_id": s.file_submission_id,
                    "student_id": s.student_id,
                    "student_moodle_id": s.student_moodle_id,
                    "activity_id": s.activity_id,
                    "activity_moodle_id": s.activity_moodle_id,
                    "joined_at": s.joined_at.isoformat() if s.joined_at else None,
                    "sent_to_moodle": s.sent_to_moodle,
                    "sent_to_moodle_at": s.sent_to_moodle_at.isoformat() if s.sent_to_moodle_at else None
                }
                for s in submissions
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_files():
        """Get all file submissions from database"""
        db = get_db_session()
        try:
            files = db.query(FileSubmissionDB).all()
            return [
                {
                    "id": f.id,
                    "activity_id": f.activity_id,
                    "activity_moodle_id": f.activity_moodle_id,
                    "file_name": f.file_name,
                    "file_path": f.file_path,
                    "file_size": f.file_size,
                    "file_type": f.file_type,
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                    "uploaded_by": f.uploaded_by,
                    "uploaded_by_moodle_id": f.uploaded_by_moodle_id,
                    "group_code": f.group_code,
                    "max_group_members": f.max_group_members
                }
                for f in files
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_all_grades():
        """Get all grades from database"""
        db = get_db_session()
        try:
            grades = db.query(GradeDB).all()
            return [
                {
                    "id": g.id,
                    "file_submission_id": g.file_submission_id,
                    "score": g.score,
                    "comment": g.comment,
                    "created_at": g.created_at.isoformat() if g.created_at else None
                }
                for g in grades
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_statistics():
        """Get overall system statistics"""
        db = get_db_session()
        try:
            moodle_count = db.query(MoodleDB).count()
            course_count = db.query(CourseDB).count()
            activity_count = db.query(ActivityDB).count()
            user_count = db.query(UserDB).count()
            submission_count = db.query(StudentSubmissionDB).count()
            file_count = db.query(FileSubmissionDB).count()
            grade_count = db.query(GradeDB).count()
            
            return {
                "moodle_instances": moodle_count,
                "courses": course_count,
                "activities": activity_count,
                "users": user_count,
                "submissions": submission_count,
                "files": file_count,
                "grades": grade_count
            }
        finally:
            db.close()
