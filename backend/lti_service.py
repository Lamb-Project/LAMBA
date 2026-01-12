import hashlib
import hmac
import base64
import time
import urllib.parse
import uuid
import requests
import os
import logging
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from typing import Dict, Any
from database import get_db_session
from db_models import StudentSubmissionDB, GradeDB, FileSubmissionDB, CourseDB, ActivityDB, MoodleDB


class LTIGradeService:
    """Service for sending grades to Moodle via LTI 1.1 Outcome Service"""

    @staticmethod
    def oauth_escape(s: str) -> str:
        """Percent-encode according to RFC 5849 (OAuth 1.0)."""
        return urllib.parse.quote(str(s), safe="~-._")

    @staticmethod
    def normalize_url_for_oauth(url: str) -> str:
        """Normalize URL per OAuth 1.0 spec."""
        p = urllib.parse.urlparse(url)
        scheme = p.scheme.lower()
        netloc = p.hostname.lower() if p.hostname else ""
        port = p.port
        if port:
            if (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
                netloc = f"{netloc}:{port}"
        path = p.path or "/"
        return f"{scheme}://{netloc}{path}"

    @staticmethod
    def generate_oauth_signature(method: str, url: str, params: dict, consumer_secret: str) -> str:
        """Generate OAuth 1.0a HMAC-SHA1 signature manually."""
        encoded_params = []
        for key, value in params.items():
            encoded_key = LTIGradeService.oauth_escape(key)
            encoded_value = LTIGradeService.oauth_escape(value)
            encoded_params.append((encoded_key, encoded_value))
        encoded_params.sort()
        normalized_params = "&".join([f"{k}={v}" for k, v in encoded_params])

        normalized_url = LTIGradeService.normalize_url_for_oauth(url)
        base_elems = [
            method.upper(),
            LTIGradeService.oauth_escape(normalized_url),
            LTIGradeService.oauth_escape(normalized_params),
        ]
        base_string = "&".join(base_elems)

        signing_key = f"{LTIGradeService.oauth_escape(consumer_secret)}&"
        hashed = hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1)
        signature = base64.b64encode(hashed.digest()).decode("utf-8")

        logging.debug(f"LTI Signature base string: {base_string}")
        logging.debug(f"LTI Signature key: {signing_key}")
        logging.debug(f"LTI Signature: {signature}")

        return signature

    @staticmethod
    def create_outcome_xml(sourcedid: str, score: float, comment: str) -> str:
        """Create XML payload for LTI Outcome Service. Normalize score to 0..1 (assuming input 0..10)."""
        message_identifier = str(uuid.uuid4())
        # Always normalize score from 0-10 scale to 0-1 scale for LTI
        normalized_score = max(0.0, min(1.0, float(score) / 10.0))

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<imsx_POXEnvelopeRequest xmlns="http://www.imsglobal.org/services/ltiv1p1/xsd/imsoms_v1p0">
    <imsx_POXHeader>
        <imsx_POXRequestHeaderInfo>
            <imsx_version>V1.0</imsx_version>
            <imsx_messageIdentifier>{escape(message_identifier)}</imsx_messageIdentifier>
        </imsx_POXRequestHeaderInfo>
    </imsx_POXHeader>
    <imsx_POXBody>
        <replaceResultRequest>
            <resultRecord>
                <sourcedGUID>
                    <sourcedId>{escape(sourcedid)}</sourcedId>
                </sourcedGUID>
                <result>
                    <resultScore>
                        <language>en</language>
                        <textString>{normalized_score}</textString>
                    </resultScore>
                    <resultData>
                        <text>{escape(comment)}</text>
                    </resultData>
                </result>
            </resultRecord>
        </replaceResultRequest>
    </imsx_POXBody>
</imsx_POXEnvelopeRequest>"""

    @staticmethod
    def send_grade_to_moodle(
        lis_result_sourcedid: str,
        lis_outcome_service_url: str,
        oauth_consumer_key: str,
        oauth_consumer_secret: str,
        score: float,
        comment: str = "Calificación enviada automáticamente",
    ) -> Dict[str, Any]:
        """Send a single grade to Moodle (LTI 1.1 Outcome Service)."""
        try:
            logging.info(f"Sending grade to Moodle - Score: {score}/10, Comment: {comment}")
            xml_payload = LTIGradeService.create_outcome_xml(lis_result_sourcedid, score, comment)

            # Calculate oauth_body_hash
            body_hash = hashlib.sha1(xml_payload.encode("utf-8")).digest()
            oauth_body_hash = base64.b64encode(body_hash).decode("utf-8")

            oauth_params = {
                "oauth_consumer_key": oauth_consumer_key,
                "oauth_nonce": str(uuid.uuid4()).replace("-", ""),
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_timestamp": str(int(time.time())),
                "oauth_version": "1.0",
                "oauth_body_hash": oauth_body_hash,
            }

            signature = LTIGradeService.generate_oauth_signature(
                "POST", lis_outcome_service_url, oauth_params, oauth_consumer_secret
            )
            oauth_params["oauth_signature"] = signature

            # Build Authorization header
            auth_header_parts = []
            for k, v in sorted(oauth_params.items()):
                auth_header_parts.append(f'{k}="{LTIGradeService.oauth_escape(str(v))}"')
            auth_header = "OAuth " + ", ".join(auth_header_parts)

            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/xml",
                "Content-Length": str(len(xml_payload.encode("utf-8"))),
            }

            response = requests.post(
                lis_outcome_service_url, data=xml_payload.encode("utf-8"), headers=headers, timeout=30
            )

            logging.info(f"Response code: {response.status_code}")
            logging.debug(f"Response body: {response.text}")

            success = False
            error_message = None
            if response.status_code == 200:
                if "imsx_codemajor>success" in response.text.lower():
                    success = True
                    logging.info("✅ Grade sent successfully!")
                else:
                    if "signature not valid" in response.text.lower():
                        error_message = "Error: OAuth signature invalid."
                    else:
                        error_message = "Error: Moodle returned failure."
            else:
                error_message = f"Error: HTTP {response.status_code}"

            return {
                "success": success,
                "status_code": response.status_code,
                "response_text": response.text,
                "error_message": error_message,
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "status_code": None, "response_text": None, "error_message": f"Connection error: {e}"}
        except Exception as e:
            return {"success": False, "status_code": None, "response_text": None, "error_message": f"Unexpected error: {e}"}

    @staticmethod
    def send_activity_grades_to_moodle(activity_id: str, activity_moodle_id: str) -> Dict[str, Any]:
        """Send all grades for an activity to Moodle.
        
        Args:
            activity_id: Activity ID from LTI
            activity_moodle_id: Moodle instance ID
        """
        db = get_db_session()
        try:
            oauth_consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
            oauth_consumer_secret = os.getenv("LTI_SECRET")

            if not oauth_consumer_key or not oauth_consumer_secret:
                return {"success": False, "error": "LTI credentials not configured", "sent_count": 0, "failed_count": 0, "results": []}

            # Get activity using composite key
            activity = db.query(ActivityDB).filter(
                ActivityDB.id == activity_id,
                ActivityDB.course_moodle_id == activity_moodle_id
            ).first()
            if not activity:
                return {"success": False, "error": "Activity not found", "sent_count": 0, "failed_count": 0, "results": []}

            # Get course using composite key (course_id + moodle_id)
            course = db.query(CourseDB).filter(
                CourseDB.id == activity.course_id,
                CourseDB.moodle_id == activity.course_moodle_id
            ).first()
            if not course:
                return {"success": False, "error": "Course not found", "sent_count": 0, "failed_count": 0, "results": []}
            
            # Get lis_outcome_service_url from associated Moodle instance
            if not course.moodle_id:
                return {"success": False, "error": "Course is not associated with a Moodle instance", "sent_count": 0, "failed_count": 0, "results": []}
            
            moodle = db.query(MoodleDB).filter(MoodleDB.id == course.moodle_id).first()
            if not moodle or not moodle.lis_outcome_service_url:
                return {"success": False, "error": "Moodle instance not found or LTI outcome URL missing", "sent_count": 0, "failed_count": 0, "results": []}

            submissions_with_grades = (
                db.query(StudentSubmissionDB, GradeDB, FileSubmissionDB)
                .join(FileSubmissionDB, StudentSubmissionDB.file_submission_id == FileSubmissionDB.id)
                .join(GradeDB, FileSubmissionDB.id == GradeDB.file_submission_id)
                .filter(StudentSubmissionDB.activity_id == activity_id, StudentSubmissionDB.lis_result_sourcedid.isnot(None))
                .all()
            )

            if not submissions_with_grades:
                return {"success": False, "error": "No graded submissions found", "sent_count": 0, "failed_count": 0, "results": []}

            results, sent_count, failed_count = [], 0, 0
            for student_submission, grade, _ in submissions_with_grades:
                result = LTIGradeService.send_grade_to_moodle(
                    lis_result_sourcedid=student_submission.lis_result_sourcedid,
                    lis_outcome_service_url=moodle.lis_outcome_service_url,
                    oauth_consumer_key=oauth_consumer_key,
                    oauth_consumer_secret=oauth_consumer_secret,
                    score=grade.score,
                    comment=grade.comment or "Calificación enviada automáticamente",
                )

                results.append({
                    "student_id": student_submission.student_id,
                    "score": grade.score,
                    "comment": grade.comment,
                    "success": result["success"],
                    "error_message": result.get("error_message"),
                })

                if result["success"]:
                    # Mark the student submission as sent to Moodle
                    student_submission.sent_to_moodle = True
                    student_submission.sent_to_moodle_at = datetime.now(timezone.utc)
                    db.commit()
                    sent_count += 1
                else:
                    failed_count += 1

            return {
                "success": sent_count > 0 and failed_count == 0,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_submissions": len(submissions_with_grades),
                "activity_title": activity.title,
                "course_title": course.title,
                "results": results,
            }

        except Exception as e:
            logging.error(f"Error sending activity grades: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}", "sent_count": 0, "failed_count": 0, "results": []}
        finally:
            db.close()
