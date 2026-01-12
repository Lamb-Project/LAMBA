from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from models import Moodle
from db_models import MoodleDB
from database import get_db_session

class MoodleService:
    
    @staticmethod
    def create_or_update_moodle(moodle_id: str, name: str, lis_outcome_service_url: Optional[str] = None) -> Moodle:
        """Create a new Moodle instance or update existing one from LTI data"""
        db = get_db_session()
        try:
            # Check if Moodle instance already exists
            existing_moodle = db.query(MoodleDB).filter(MoodleDB.id == moodle_id).first()

            if existing_moodle:
                # Update existing Moodle instance data
                existing_moodle.name = name
                # Only update lis_outcome_service_url if it's provided and not already set
                if lis_outcome_service_url and not existing_moodle.lis_outcome_service_url:
                    existing_moodle.lis_outcome_service_url = lis_outcome_service_url
                db.commit()
                
                return Moodle(
                    id=existing_moodle.id,
                    name=existing_moodle.name,
                    lis_outcome_service_url=existing_moodle.lis_outcome_service_url,
                    created_at=existing_moodle.created_at
                )
            
            # Create new Moodle instance
            db_moodle = MoodleDB(
                id=moodle_id,
                name=name,
                lis_outcome_service_url=lis_outcome_service_url,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(db_moodle)
            db.commit()
            db.refresh(db_moodle)
            
            return Moodle(
                id=db_moodle.id,
                name=db_moodle.name,
                lis_outcome_service_url=db_moodle.lis_outcome_service_url,
                created_at=db_moodle.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_moodle_by_id(moodle_id: str) -> Optional[Moodle]:
        """Get Moodle instance by ID"""
        db = get_db_session()
        try:
            db_moodle = db.query(MoodleDB).filter(MoodleDB.id == moodle_id).first()
            if not db_moodle:
                return None
            
            return Moodle(
                id=db_moodle.id,
                name=db_moodle.name,
                lis_outcome_service_url=db_moodle.lis_outcome_service_url,
                created_at=db_moodle.created_at
            )
        finally:
            db.close()
    
    @staticmethod
    def get_all_moodles() -> List[Moodle]:
        """Get all Moodle instances"""
        db = get_db_session()
        try:
            db_moodles = db.query(MoodleDB).all()
            return [
                Moodle(
                    id=db_moodle.id,
                    name=db_moodle.name,
                    lis_outcome_service_url=db_moodle.lis_outcome_service_url,
                    created_at=db_moodle.created_at
                )
                for db_moodle in db_moodles
            ]
        finally:
            db.close()

