import sqlite3
import re
from datetime import datetime
from constants import STATES_LIST

DB_PATH = 'student_state.db'

def process_secure_request(action_type, student_id, session_token, active_token, payload):
    """
    Zero-Trust interceptor. Validates all inputs and tokens before touching the DB.
    Ensures structural integrity and prevents injection attacks.
    """
    # 1. Identity & Session Verification
    if not session_token or session_token != active_token:
        return {"status": "error", "message": "Security Alert: Invalid or expired session token."}
    
    if not re.match(r'^[a-zA-Z0-9_]+$', student_id):
        return {"status": "error", "message": "Security Alert: Invalid student ID format."}

    # 2. Payload Validation & Execution
    if action_type == "SAVE_PROFILE":
        state_code = payload.get("state_code")
        grad_year = payload.get("graduation_year")

        if state_code not in STATES_LIST:
            return {"status": "error", "message": "Validation Error: Invalid state code."}
        
        try:
            grad_year = int(grad_year)
            if not (2026 <= grad_year <= 2032):
                raise ValueError
        except (ValueError, TypeError):
            return {"status": "error", "message": "Validation Error: Graduation year must be between 2026 and 2032."}

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE students SET state_code = ?, graduation_year = ? WHERE student_id = ?", 
                      (state_code, grad_year, student_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Profile updated successfully."}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    elif action_type == "LOG_SCORES":
        test_date = payload.get("test_date")
        math_score = payload.get("math_score")
        rw_score = payload.get("reading_writing_score")

        try:
            datetime.strptime(test_date, "%Y-%m-%d")
            math_score = int(math_score)
            rw_score = int(rw_score)
            if not (160 <= math_score <= 800) or not (160 <= rw_score <= 800):
                 return {"status": "error", "message": "Validation Error: Scores must be within valid testing ranges."}
        except (ValueError, TypeError):
            return {"status": "error", "message": "Validation Error: Invalid score or date format."}

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            sat_total = math_score + rw_score
            c.execute('''
                INSERT INTO practice_scores (student_id, test_date, sat_total_score, math_score, reading_writing_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, test_date, sat_total, math_score, rw_score))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Scores logged successfully."}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    elif action_type == "UPDATE_SYLLABUS":
        topic = payload.get("topic")
        is_completed = payload.get("is_completed")
        
        # Basic type validation
        if not isinstance(topic, str) or is_completed not in [0, 1]:
            return {"status": "error", "message": "Validation Error: Invalid syllabus data."}
            
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Upsert: Insert new topic progress, or update existing topic state
            c.execute('''
                INSERT INTO syllabus_progress (student_id, topic, is_completed)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, topic) DO UPDATE SET is_completed=excluded.is_completed
            ''', (student_id, topic, is_completed))
            conn.commit()
            conn.close()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    return {"status": "error", "message": "Security Alert: Unknown action type."}