import os
import re
import shutil
from datetime import datetime, timezone
from typing import Optional


class FileStorageService:
    """Utility helpers to manage the uploads directory structure."""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOADS_ROOT = os.path.join(BASE_DIR, "uploads")

    @classmethod
    def ensure_uploads_root(cls) -> str:
        os.makedirs(cls.UPLOADS_ROOT, exist_ok=True)
        return cls.UPLOADS_ROOT

    @classmethod
    def ensure_moodle_directory(cls, moodle_id: str) -> str:
        """Create moodle instance directory if it doesn't exist"""
        moodle_dir = os.path.join(cls.ensure_uploads_root(), moodle_id)
        os.makedirs(moodle_dir, exist_ok=True)
        return moodle_dir

    @classmethod
    def ensure_course_directory(cls, moodle_id: str, course_id: str) -> str:
        """Create course directory inside moodle directory if it doesn't exist"""
        course_dir = os.path.join(cls.ensure_moodle_directory(moodle_id), course_id)
        os.makedirs(course_dir, exist_ok=True)
        return course_dir

    @classmethod
    def ensure_activity_directory(cls, moodle_id: str, course_id: str, activity_id: str) -> str:
        """Create activity directory inside course directory if it doesn't exist"""
        activity_dir = os.path.join(cls.ensure_course_directory(moodle_id, course_id), activity_id)
        os.makedirs(activity_dir, exist_ok=True)
        return activity_dir

    @classmethod
    def save_submission_file(
        cls,
        *,
        moodle_id: str,
        course_id: str,
        activity_id: str,
        submission_id: str,
        file_name: str,
        file_bytes: bytes,
        previous_file_path: Optional[str] = None
    ) -> str:
        """
        Persist a submission file inside uploads/<moodle_id>/<course_id>/<activity_id>.
        Returns the relative path (from BASE_DIR) that should be stored in the DB.
        """
        activity_dir = cls.ensure_activity_directory(moodle_id, course_id, activity_id)

        if previous_file_path:
            cls.delete_path(previous_file_path)

        sanitized_name = cls._sanitize_filename(file_name)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        destination_name = f"{submission_id}_{timestamp}_{sanitized_name}"
        destination_path = os.path.join(activity_dir, destination_name)

        with open(destination_path, "wb") as destination_file:
            destination_file.write(file_bytes)

        return cls._to_relative_path(destination_path)

    @classmethod
    def resolve_path(cls, path: str) -> str:
        """Return an absolute path for a stored file (handles relative DB paths)."""
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(cls.BASE_DIR, path))

    @classmethod
    def is_within_uploads(cls, path: str) -> bool:
        """Ensure the provided path stays inside the uploads root."""
        uploads_root = cls.ensure_uploads_root()
        abs_path = os.path.abspath(path)
        try:
            common_path = os.path.commonpath([abs_path, uploads_root])
        except ValueError:
            return False
        return common_path == uploads_root

    @classmethod
    def delete_path(cls, path: str) -> None:
        """Delete a file or directory if it exists (used for cleanup)."""
        if not path:
            return
        abs_path = cls.resolve_path(path)
        if not cls.is_within_uploads(abs_path):
            return

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path, ignore_errors=True)
        elif os.path.isfile(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass

    @classmethod
    def _to_relative_path(cls, absolute_path: str) -> str:
        try:
            return os.path.relpath(absolute_path, start=cls.BASE_DIR)
        except ValueError:
            # On Windows mixing drive letters can raise ValueError; fallback to absolute
            return absolute_path

    @staticmethod
    def sanitize_filename(file_name: str) -> str:
        """Public helper to sanitize filenames consistently."""
        return FileStorageService._sanitize_filename(file_name)

    @staticmethod
    def _sanitize_filename(file_name: str) -> str:
        base_name = os.path.basename(file_name or "")
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base_name).strip("._")
        return cleaned or "submission"

