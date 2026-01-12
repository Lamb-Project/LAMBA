from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from models import User, UserRole
from db_models import UserDB
from database import get_db_session

class UserService:
    
    @staticmethod
    def create_or_update_user(user_id: str, moodle_id: str, full_name: str, email: Optional[str], roles: str) -> User:
        """Create a new user or update existing user from LTI data
        
        Args:
            user_id: User ID from LTI
            moodle_id: Moodle instance ID (part of composite key)
            full_name: User's full name
            email: User's email
            roles: LTI roles string
        """
        db = get_db_session()
        try:
            # Determine user role based on LTI roles
            role = UserRole.TEACHER if any(role in roles.lower() for role in ['administrator', 'instructor', 'teacher', 'admin']) else UserRole.STUDENT
            
            # Check if user already exists (using composite key)
            existing_user = db.query(UserDB).filter(
                UserDB.id == user_id,
                UserDB.moodle_id == moodle_id
            ).first()
            if existing_user:
                # Update existing user data
                existing_user.full_name = full_name
                existing_user.email = email
                existing_user.role = role
                db.commit()
                
                # Convert to Pydantic model
                return User(
                    id=existing_user.id,
                    moodle_id=existing_user.moodle_id,
                    full_name=existing_user.full_name,
                    email=existing_user.email,
                    role=existing_user.role,
                    created_at=existing_user.created_at
                )
            
            # Create new user
            db_user = UserDB(
                id=user_id,
                moodle_id=moodle_id,
                full_name=full_name,
                email=email,
                role=role,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Convert to Pydantic model
            return User(
                id=db_user.id,
                moodle_id=db_user.moodle_id,
                full_name=db_user.full_name,
                email=db_user.email,
                role=db_user.role,
                created_at=db_user.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_user_by_id(user_id: str, moodle_id: str) -> Optional[User]:
        """Get user by composite ID (user_id + moodle_id)
        
        Args:
            user_id: User ID from LTI
            moodle_id: Moodle instance ID
        """
        db = get_db_session()
        try:
            db_user = db.query(UserDB).filter(
                UserDB.id == user_id,
                UserDB.moodle_id == moodle_id
            ).first()
            if not db_user:
                return None
            
            return User(
                id=db_user.id,
                moodle_id=db_user.moodle_id,
                full_name=db_user.full_name,
                email=db_user.email,
                role=db_user.role,
                created_at=db_user.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_all_users() -> List[User]:
        """Get all users"""
        db = get_db_session()
        try:
            db_users = db.query(UserDB).all()
            return [
                User(
                    id=user.id,
                    moodle_id=user.moodle_id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                    created_at=user.created_at
                ) for user in db_users
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_users_count() -> int:
        """Get total number of users"""
        db = get_db_session()
        try:
            return db.query(UserDB).count()
        finally:
            db.close()
    
    @staticmethod
    def get_users_by_role(role: str) -> List[User]:
        """Get users by role"""
        db = get_db_session()
        try:
            db_users = db.query(UserDB).filter(UserDB.role == role).all()
            return [
                User(
                    id=user.id,
                    moodle_id=user.moodle_id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                    created_at=user.created_at
                ) for user in db_users
            ]
        finally:
            db.close()
    
    @staticmethod
    def get_teachers() -> List[User]:
        """Get all teachers"""
        return UserService.get_users_by_role(UserRole.TEACHER)
    
    @staticmethod
    def get_students() -> List[User]:
        """Get all students"""
        return UserService.get_users_by_role(UserRole.STUDENT)
