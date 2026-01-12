from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Course
from db_models import CourseDB
from database import get_db_session
from storage_service import FileStorageService

class CourseService:
    
    @staticmethod
    def create_or_update_course(course_id: str, title: str, moodle_id: str) -> Course:
        """Create a new course or update existing course from LTI data
        
        Args:
            course_id: Course ID from LTI (context_id)
            title: Course title
            moodle_id: Moodle instance ID (required - part of composite key)
        """
        db = get_db_session()
        try:
            # Check if course already exists (using composite key)
            existing_course = db.query(CourseDB).filter(
                CourseDB.id == course_id,
                CourseDB.moodle_id == moodle_id
            ).first()
            
            # Ensure course directory exists in filesystem with moodle_id structure
            if course_id and moodle_id:
                FileStorageService.ensure_course_directory(moodle_id, course_id)

            if existing_course:
                # Update existing course data
                existing_course.title = title
                db.commit()
                
                return Course(
                    id=existing_course.id,
                    title=existing_course.title,
                    moodle_id=existing_course.moodle_id,
                    created_at=existing_course.created_at
                )
            
            # Create new course
            db_course = CourseDB(
                id=course_id,
                title=title,
                moodle_id=moodle_id,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(db_course)
            db.commit()
            db.refresh(db_course)
            
            return Course(
                id=db_course.id,
                title=db_course.title,
                moodle_id=db_course.moodle_id,
                created_at=db_course.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_course_by_id(course_id: str, moodle_id: str) -> Optional[Course]:
        """Get course by composite ID (course_id + moodle_id)
        
        Args:
            course_id: Course ID from LTI (context_id)
            moodle_id: Moodle instance ID
        """
        db = get_db_session()
        try:
            db_course = db.query(CourseDB).filter(
                CourseDB.id == course_id,
                CourseDB.moodle_id == moodle_id
            ).first()
            if not db_course:
                return None
            
            return Course(
                id=db_course.id,
                title=db_course.title,
                moodle_id=db_course.moodle_id,
                created_at=db_course.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_all_courses() -> List[Course]:
        """Get all courses"""
        db = get_db_session()
        try:
            db_courses = db.query(CourseDB).all()
            return [
                Course(
                    id=course.id,
                    title=course.title,
                    moodle_id=course.moodle_id,
                    created_at=course.created_at
                ) for course in db_courses
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_courses_count() -> int:
        """Get total number of courses"""
        db = get_db_session()
        try:
            return db.query(CourseDB).count()
        finally:
            db.close()
    
    @staticmethod
    def delete_course(course_id: str) -> bool:
        """Delete a course"""
        db = get_db_session()
        try:
            db_course = db.query(CourseDB).filter(CourseDB.id == course_id).first()
            if db_course:
                db.delete(db_course)
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    @staticmethod
    def search_courses_by_title(title_query: str) -> List[Course]:
        """Search courses by title (case insensitive)"""
        db = get_db_session()
        try:
            db_courses = db.query(CourseDB).filter(
                CourseDB.title.ilike(f"%{title_query}%")
            ).all()
            return [
                Course(
                    id=course.id,
                    title=course.title,
                    moodle_id=course.moodle_id,
                    created_at=course.created_at
                ) for course in db_courses
            ]
        finally:
            db.close()
