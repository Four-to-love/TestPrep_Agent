import sqlite3
import re
from datetime import datetime
from constants import STATES_LIST
# ==========================================
# AGENT IMPORTS
# ==========================================
from agents.tutor import SyllabusTutorAgent
from agents.topic_expander import TopicExpanderAgent
from agents.strategist import StrategistAgent

# ==========================================
# SKILL IMPORTS
# ==========================================
from agents.skills.nmsi_calculator.nmsi_calculator import calculate_selection_index, get_state_target
from agents.skills.curriculum_mapper.scheduler_skill import generate_schedule
from agents.skills.test_date_calculator.date_engine import calculate_test_date
from agents.skills.syllabus_renderer import render_syllabus_timeline
from agents.skills.calendar_export.export_ics import export_schedule_to_ics

# Import any other skills here!


import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'student_state.db')

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
        has_test_date = "target_test_date" in payload
        target_test_date = payload.get("target_test_date")

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
            
            if has_test_date:
                c.execute('''
                    INSERT INTO students (student_id, state_code, graduation_year, target_test_date)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(student_id) DO UPDATE SET 
                        state_code=excluded.state_code, 
                        graduation_year=excluded.graduation_year,
                        target_test_date=excluded.target_test_date
                ''', (student_id, state_code, grad_year, target_test_date))
            else:
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

    elif action_type == "GET_STUDENT":
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT state_code, graduation_year, target_test_date FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()
            if not row:
                c.execute("INSERT INTO students (student_id, state_code, graduation_year, target_test_date) VALUES (?, ?, ?, ?)",
                          (student_id, "WA", 2028, ""))
                conn.commit()
                c.execute("SELECT state_code, graduation_year, target_test_date FROM students WHERE student_id = ?", (student_id,))
                row = c.fetchone()
            conn.close()
            return {"status": "success", "data": dict(row)}
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
            
            # 1. Get Best Score (highest total score row)
            c.execute("SELECT sat_total_score as best_score, math_score as best_math, reading_writing_score as best_rw, date_test_taken FROM practice_scores WHERE student_id = ? ORDER BY sat_total_score DESC, id DESC LIMIT 1", (student_id,))
            best_row = c.fetchone()
            if best_row:
                best_score = best_row["best_score"] if best_row["best_score"] else 0
                best_math = best_row["best_math"] if best_row["best_math"] else 0
                best_rw = best_row["best_rw"] if best_row["best_rw"] else 0
                best_date = best_row["date_test_taken"] if best_row["date_test_taken"] else "No tests logged"
            else:
                best_score = 0
                best_math = 0
                best_rw = 0
                best_date = "No tests logged"
        
            # 2. Get Last 5 Scores
            c.execute("SELECT date_test_taken as Date, reading_writing_score as RW, math_score as Math, sat_total_score as Total FROM practice_scores WHERE student_id = ? ORDER BY id DESC LIMIT 5", (student_id,))
            recent_scores = [dict(row) for row in c.fetchall()]
        
            # 3. Get Student Profile Details
            c.execute("SELECT state_code, graduation_year, target_test_date FROM students WHERE student_id = ?", (student_id,))
            state_row = c.fetchone()
            state_code = state_row["state_code"] if state_row else "WA"
            grad_year = state_row["graduation_year"] if state_row else None
            db_test_date = state_row["target_test_date"] if state_row else None
        
            # Call YOUR NMSI Engine 
            target_cutoff = get_state_target(state_code)
            
            # 4. Calculate Pacing Strategy and Focus via Strategist (Zero-Trust Interceptor Execution)
            overall_focus = ""
            pacing_strategy = ""
            if grad_year:
                # Fetch latest scores for weighting
                c.execute("SELECT math_score, reading_writing_score FROM practice_scores WHERE student_id = ? ORDER BY id DESC LIMIT 1", (student_id,))
                last_score = c.fetchone()
                last_math = last_score["math_score"] if last_score else 500
                last_rw = last_score["reading_writing_score"] if last_score else 500
                
                # Fetch mastered skills to filter out
                c.execute("SELECT topic FROM syllabus_progress WHERE student_id = ? AND is_completed = 1", (student_id,))
                mastered_skills = [row["topic"] for row in c.fetchall()]
                
                agent = StrategistAgent()
                blueprint = agent.generate_adaptive_timeline(
                    graduation_year=grad_year,
                    test_date_str=db_test_date,
                    math_score=last_math,
                    rw_score=last_rw,
                    mastered_skills=mastered_skills
                )
                if "error" not in blueprint:
                    overall_focus = blueprint.get("overall_focus", "")
                    pacing_strategy = blueprint.get("pacing_strategy", "")
            
            conn.close()
            
            return {
                "status": "success", 
                "data": {
                    "best_score": best_score,
                    "best_math": best_math,
                    "best_rw": best_rw,
                    "best_date": best_date,
                    "recent_scores": recent_scores,
                    "state_code": state_code,
                    "nmsi_cutoff": target_cutoff,
                    "overall_focus": overall_focus,
                    "pacing_strategy": pacing_strategy
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

    elif action_type == "GET_SYLLABUS":
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT topic, is_completed FROM syllabus_progress WHERE student_id = ?", (student_id,))
            rows = c.fetchall()
            conn.close()
            
            mastered_topics = [row[0] for row in rows if row[1] == 1]
            return {"status": "success", "data": mastered_topics}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    # --- NEW: Connecting the DB to the Strategist ---
    elif action_type == "GENERATE_PLAN":
        test_date_str = payload.get("test_date")
        
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # 1. Fetch Profile (Graduation Year & Target Test Date)
            c.execute("SELECT graduation_year, target_test_date FROM students WHERE student_id = ?", (student_id,))
            profile_row = c.fetchone()
            if not profile_row or not profile_row[0]:
                 conn.close()
                 return {"status": "error", "message": "No profile found. Please save your graduation year first."}
            grad_year = profile_row[0]
            db_test_date = profile_row[1]
            
            # Determine test_date
            if not test_date_str:
                test_date_str = db_test_date
                
            if not test_date_str:
                # Use date_engine calculation
                calc = calculate_test_date(grad_year)
                if "error" in calc:
                    conn.close()
                    return {"status": "error", "message": calc["error"]}
                test_date_str = calc["test_date"]

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

# ==========================================
    # --- NEW: AGENT & SKILL DIRECT ROUTES ---
    # ==========================================
    elif action_type == "TUTOR_CHAT":
        tutor = SyllabusTutorAgent()
        message = payload.get("message", "")
        recent_context = payload.get("recent_context", [])
        return {"status": "success", "data": tutor.answer_question(message, recent_context)}

    elif action_type == "EXPAND_TOPIC":
        expander = TopicExpanderAgent()
        topic_name = payload.get("topic_name", "")
        return {"status": "success", "data": expander.expand_topic(topic_name)}

    elif action_type == "CALCULATE_NMSI":
        # 1. Grab the scores dictionary from the payload
        scores = payload.get("scores", {})
        
        # 2. Extract the individual numbers (defaulting to 0 if missing)
        rw_score = scores.get("rw", 0)
        math_score = scores.get("math", 0)
        
        # 3. Pass them as two separate positional arguments, just like the function expects!
        return {"status": "success", "data": calculate_selection_index(rw_score, math_score)}

    elif action_type == "GET_STATE_TARGET":
        state_code = payload.get("state", "WA")
        return {"status": "success", "data": get_state_target(state_code)}

    elif action_type == "CALCULATE_TEST_DATE":
        # Pass the entire payload as keyword arguments safely
        payload = payload or {} 
        return {"status": "success", "data": calculate_test_date(**payload)}

    elif action_type == "GENERATE_SCHEDULE":
        payload = payload or {}
        return {"status": "success", "data": generate_schedule(**payload)}

    elif action_type == "RENDER_SYLLABUS":
        syllabus_file = payload.get("syllabus_file")
        marker_class = payload.get("marker_class")
        key_prefix = payload.get("key_prefix")
        column_label = payload.get("column_label", "Task")
        
        render_syllabus_timeline(
            syllabus_file=syllabus_file,
            marker_class=marker_class,
            key_prefix=key_prefix,
            student_id=student_id,
            session_token=session_token,
            active_token=active_token,
            column_label=column_label
        )
        return {"status": "success"}

    elif action_type == "EXPORT_ICS":
        schedule_df = payload.get("schedule_df")
        if schedule_df is None:
            return {"status": "error", "message": "Validation Error: schedule_df is required."}
        try:
            ics_path = export_schedule_to_ics(schedule_df)
            return {"status": "success", "data": {"ics_path": ics_path}}
        except Exception as e:
            return {"status": "error", "message": f"ICS Export Error: {str(e)}"}


    return {"status": "error", "message": "Security Alert: Unknown action type."}