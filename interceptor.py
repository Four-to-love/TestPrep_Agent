import sqlite3
import re
from datetime import datetime
from constants import STATES_LIST
from agents.strategist import StrategistAgent
from agents.skills.nmsi_calculator.nmsi_calculator import get_state_target

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
            
            # THE FIX: Using an Upsert instead of a standard Update
            c.execute('''
                INSERT INTO students (student_id, state_code, graduation_year)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET 
                    state_code=excluded.state_code, 
                    graduation_year=excluded.graduation_year
            ''', (student_id, state_code, grad_year))
            
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Profile updated successfully."}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    elif action_type == "LOG_SCORES":
        date_test_taken = payload.get("date_test_taken")
        math_score = payload.get("math_score")
        rw_score = payload.get("reading_writing_score")

        try:
            datetime.strptime(date_test_taken, "%Y-%m-%d")
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
                INSERT INTO practice_scores (student_id, date_test_taken, sat_total_score, math_score, reading_writing_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, date_test_taken, sat_total, math_score, rw_score))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Scores logged successfully."}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    elif action_type == "GET_ANALYTICS":
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row # This lets us return data as dictionaries
            c = conn.cursor()
            
            # 1. Get Best Score
            c.execute("SELECT MAX(sat_total_score) as best_score, date_test_taken FROM practice_scores WHERE student_id = ?", (student_id,))
            best_row = c.fetchone()
            best_score = best_row["best_score"] if best_row["best_score"] else 0
            best_date = best_row["date_test_taken"] if best_row["best_score"] else "No tests logged"
        
            # 2. Get Last 5 Scores
            c.execute("SELECT date_test_taken as Date, reading_writing_score as RW, math_score as Math, sat_total_score as Total FROM practice_scores WHERE student_id = ? ORDER BY date_test_taken DESC LIMIT 5", (student_id,))
            recent_scores = [dict(row) for row in c.fetchall()]
        
            # 3. Get State for NMSI
            c.execute("SELECT state_code FROM students WHERE student_id = ?", (student_id,))
            state_row = c.fetchone()
            state_code = state_row["state_code"] if state_row else "WA"
        
            # Call YOUR NMSI Engine 
            target_cutoff = get_state_target(state_code)
            
            conn.close()
            
            return {
                "status": "success", 
                "data": {
                    "best_score": best_score,
                    "best_date": best_date,
                    "recent_scores": recent_scores,
                    "state_code": state_code,
                    "nmsi_cutoff": target_cutoff  # <-- THIS IS THE MISSING KEY!
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Analytics Database Error: {str(e)}"}

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

    # --- NEW: Connecting the DB to the Strategist ---
    elif action_type == "GENERATE_PLAN":
        test_date_str = payload.get("test_date")
        
        if not test_date_str:
            return {"status": "error", "message": "Validation Error: Target test date is required."}
            
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # 1. Fetch Profile (Graduation Year)
            c.execute("SELECT graduation_year FROM students WHERE student_id = ?", (student_id,))
            profile_row = c.fetchone()
            if not profile_row or not profile_row[0]:
                 return {"status": "error", "message": "No profile found. Please save your graduation year first."}
            grad_year = profile_row[0]

            # 2. Fetch Latest Scores for Weighting
            c.execute('''
                SELECT math_score, reading_writing_score FROM practice_scores 
                WHERE student_id = ? ORDER BY date_test_taken DESC LIMIT 1
            ''', (student_id,))
            score_row = c.fetchone()
            
            # If no scores exist, default to 500/500 for a Balanced Review
            if not score_row:
                 math_score, rw_score = 500, 500 
            else:
                 math_score, rw_score = score_row

            # 3. Fetch Mastered Skills to Filter Out
            c.execute("SELECT topic FROM syllabus_progress WHERE student_id = ? AND is_completed = 1", (student_id,))
            mastered_skills = [row[0] for row in c.fetchall()]
            
            conn.close()

            # 4. Generate Blueprint using the Silent Agent
            agent = StrategistAgent()
            blueprint = agent.generate_adaptive_timeline(
                graduation_year=grad_year,
                test_date_str=test_date_str,
                math_score=math_score,
                rw_score=rw_score,
                mastered_skills=mastered_skills
            )

            # Pass up any errors returned by the scheduler
            if "error" in blueprint:
                return {"status": "error", "message": blueprint["error"]}

            # Return the finalized multi-grade schedule
            return {"status": "success", "data": blueprint}

        except Exception as e:
            return {"status": "error", "message": f"Execution Error: {str(e)}"}

    return {"status": "error", "message": "Security Alert: Unknown action type."}