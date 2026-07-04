import sqlite3
import re
import os
import time
import threading
import secrets
import bcrypt
from collections import deque
from datetime import datetime, date
from constants import STATES_LIST
# ==========================================
# AGENT IMPORTS
# ==========================================
from agents.tutor import SyllabusTutorAgent
from agents.topic_expander import TopicExpanderAgent
from agents.skills.strategy_engine.strategy_engine import StrategyEngine
from agents.narrator import NarratorAgent

# ==========================================
# SKILL IMPORTS
# ==========================================
from agents.skills.nmsi_calculator.nmsi_calculator import calculate_selection_index, get_state_target
from agents.skills.curriculum_mapper.scheduler_skill import generate_schedule
from agents.skills.test_date_calculator.date_engine import calculate_test_date
from agents.skills.syllabus_renderer import render_syllabus_timeline
from agents.skills.calendar_export.export_ics import export_schedule_to_ics
from mcp_client import call_mcp_tool

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'student_state.db')

# ==========================================
# SECURE PIN HASHING  (bcrypt, work factor 12)
# Must be defined before init_credentials_table() is called below.
# ==========================================
_BCRYPT_ROUNDS = 12
_SHA256_HEX_LEN = 64  # fingerprint of legacy unsalted SHA-256 hashes

def _hash_pin(pin: str) -> str:
    """Returns a bcrypt hash of the PIN encoded as UTF-8 for DB storage."""
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")

def _verify_pin(pin: str, stored_hash: str, student_id: str) -> bool:
    """
    Verifies a PIN against its stored hash.
    Transparently migrates legacy unsalted SHA-256 hashes to bcrypt on first
    successful login so existing accounts keep working without a forced reset.
    """
    import hashlib

    # --- Legacy path: detect unsalted SHA-256 hex (64 lowercase hex chars) ---
    if len(stored_hash) == _SHA256_HEX_LEN and all(c in "0123456789abcdef" for c in stored_hash):
        legacy_hash = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        if legacy_hash != stored_hash:
            return False
        # Correct PIN — silently upgrade hash in DB
        try:
            new_hash = _hash_pin(pin)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "UPDATE student_credentials SET pin_hash = ? WHERE student_id = ?",
                (new_hash, student_id)
            )
            conn.commit()
            conn.close()
            print(f"DEBUG: PIN hash migrated to bcrypt for {student_id}")
        except Exception as e:
            print(f"DEBUG: PIN migration failed for {student_id}: {e}")
        return True

    # --- Modern path: bcrypt constant-time check ---
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False

# ==========================================
# RATE LIMITER (sliding-window, per-student)
# ==========================================
_RATE_LIMITS = {
    "TUTOR_CHAT":    {"max_calls": 15, "window_seconds": 60},
    "EXPAND_TOPIC":  {"max_calls": 8,  "window_seconds": 60},
    "GET_SUMMARIES": {"max_calls": 8,  "window_seconds": 60},
}
_rate_limit_store: dict = {}
_rate_limit_lock = threading.Lock()

def _check_rate_limit(student_id: str, action_type: str) -> dict | None:
    """
    Sliding-window rate limiter.
    Returns None if the request is allowed, or an error dict if the limit is exceeded.
    """
    config = _RATE_LIMITS.get(action_type)
    if not config:
        return None
    max_calls = config["max_calls"]
    window = config["window_seconds"]
    key = (student_id, action_type)
    now = time.monotonic()
    with _rate_limit_lock:
        if key not in _rate_limit_store:
            _rate_limit_store[key] = deque()
        timestamps = _rate_limit_store[key]
        cutoff = now - window
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()
        if len(timestamps) >= max_calls:
            wait_secs = int(window - (now - timestamps[0])) + 1
            return {
                "status": "error",
                "message": (
                    f"Rate limit reached: maximum {max_calls} requests per "
                    f"{window}s for {action_type}. "
                    f"Please wait ~{wait_secs}s before trying again."
                )
            }
        timestamps.append(now)
    return None

def init_credentials_table():
    try:
        # Idempotently bootstrap database tables
        import db_setup
        db_setup.create_database()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS student_credentials (
                student_id TEXT PRIMARY KEY,
                pin_hash TEXT
            )
        ''')

        # Migration: Add student_name column to students table if not exists
        try:
            c.execute("ALTER TABLE students ADD COLUMN student_name TEXT DEFAULT 'Student'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

        c.execute("SELECT 1 FROM student_credentials WHERE student_id = 'student_001'")
        if not c.fetchone():
            default_pin = "1234"
            pin_hash = _hash_pin(default_pin)  # bcrypt — safe because _hash_pin defined above
            c.execute("INSERT INTO student_credentials (student_id, pin_hash) VALUES (?, ?)", ("student_001", pin_hash))
            c.execute("SELECT 1 FROM students WHERE student_id = 'student_001'")
            if not c.fetchone():
                c.execute(
                    "INSERT INTO students (student_id, state_code, graduation_year, target_test_date, student_name) VALUES (?, ?, ?, ?, ?)",
                    ("student_001", "WA", 2028, "", "Alex")
                )
        else:
            c.execute(
                "UPDATE students SET student_name = 'Alex' WHERE student_id = 'student_001' "
                "AND (student_name IS NULL OR student_name = '' OR student_name = 'Student')"
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DEBUG: Failed to initialize student_credentials: {str(e)}")

# Initialize credentials database (safe: _hash_pin is defined above)
init_credentials_table()

def sanitize_input_string(s: str) -> str:
    """
    Sanitizes string inputs to prevent XSS and SQL injection patterns.
    """
    if not s:
        return ""
    return re.sub(r'[<>\'"%;()&+]', '', s)

def _validate_test_date(target_test_date: str, grad_year: int) -> str | None:
    """
    Enforces two rules:
      1. Target test date must be today or in the future.
      2. Target test date must be on or before December 1 of the student's
         junior year (grad_year - 1).
    Returns an error message string if invalid, or None if valid.
    """
    try:
        from datetime import date as _date
        test_date_obj = datetime.strptime(target_test_date, "%Y-%m-%d").date()

        if test_date_obj < _date.today():
            return (
                "Please check your test date. "
                "The date you selected is in the past. "
                "Choose an upcoming test date."
            )

        max_test_date = datetime(int(grad_year) - 1, 12, 1).date()
        if test_date_obj > max_test_date:
            return (
                f"Please check your test date. "
                f"For the class of {grad_year}, the last available SAT/PSAT testing window "
                f"is December 1, {int(grad_year) - 1} \u2014 the final test date of your junior year. "
                f"Choose a date on or before December 1, {int(grad_year) - 1}."
            )
    except (ValueError, TypeError):
        return "Invalid test date format. Please use a valid date."
    return None

def process_secure_request(action_type: str, student_id: str, session_token: str, active_token: str, payload: dict) -> dict:
    """
    Zero-Trust Security Gateway: Intercepts all client requests, validates identity,
    authenticates active session token, and sanitizes payload parameters.
    Ensures structural integrity and prevents injection attacks.
    """
    # 1. Identity & Session Verification
    # AUTHENTICATE, REGISTER_STUDENT, and AUTHENTICATE_GUEST bypass token check
    # (they ARE the token-issuance endpoints).
    if action_type not in ["AUTHENTICATE", "REGISTER_STUDENT", "AUTHENTICATE_GUEST"]:
        if not session_token or session_token != active_token:
            return {"status": "error", "message": "Security Alert: Invalid or expired session token."}

    if not re.match(r'^[a-zA-Z0-9_]+$', student_id):
        return {"status": "error", "message": "Security Alert: Invalid student ID format."}

    # 2. Payload Validation & Execution
    if action_type == "SAVE_PROFILE":
        state_code = payload.get("state_code")
        grad_year = payload.get("graduation_year")
        student_name = payload.get("student_name", "Student")

        if state_code not in STATES_LIST:
            return {"status": "error", "message": "Validation Error: Invalid state code."}

        try:
            grad_year = int(grad_year)
            if not (2027 <= grad_year <= 2035):
                raise ValueError
        except (ValueError, TypeError):
            return {"status": "error", "message": "Validation Error: Graduation year must be between 2027 and 2035."}

        # Fetch current target_test_date from the DB to preserve it without re-validating
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT target_test_date FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()
            conn.close()
            current_test_date = row[0] if row else ""
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

        try:
            resp_str = call_mcp_tool("save_student_profile", {
                "student_id": student_id,
                "state_code": sanitize_input_string(state_code),
                "graduation_year": grad_year,
                "target_test_date": current_test_date,
                "student_name": sanitize_input_string(student_name)
            })
            if resp_str.startswith("Success"):
                return {"status": "success", "message": resp_str}
            return {"status": "error", "message": resp_str}
        except Exception as e:
            return {"status": "error", "message": f"Service Connection Error: The profile update service is currently offline. Details: {str(e)}"}

    elif action_type == "SAVE_TARGET_DATE":
        target_test_date = payload.get("target_test_date", "")

        # Fetch current profile details from the DB to preserve them and use for validation
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT state_code, graduation_year, student_name FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()
            conn.close()
            if row:
                state_code, grad_year, student_name = row
            else:
                state_code, grad_year, student_name = "WA", 2028, "Student"
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

        if target_test_date:
            date_error = _validate_test_date(target_test_date, grad_year)
            if date_error:
                return {"status": "error", "message": date_error}

        try:
            resp_str = call_mcp_tool("save_student_profile", {
                "student_id": student_id,
                "state_code": sanitize_input_string(state_code),
                "graduation_year": grad_year,
                "target_test_date": sanitize_input_string(target_test_date),
                "student_name": sanitize_input_string(student_name)
            })
            if resp_str.startswith("Success"):
                return {"status": "success", "message": resp_str}
            return {"status": "error", "message": resp_str}
        except Exception as e:
            return {"status": "error", "message": f"Service Connection Error: The profile update service is currently offline. Details: {str(e)}"}

    elif action_type == "GET_STUDENT":
        try:
            import json
            resp_str = call_mcp_tool("fetch_student_profile", {"student_id": student_id})
            resp = json.loads(resp_str)
            if resp.get("status") == "success":
                data = resp.get("data")
                if student_id == "student_001" and (data.get("student_name") == "Student" or not data.get("student_name")):
                    data["student_name"] = "Alex"
                    call_mcp_tool("save_student_profile", {
                        "student_id": student_id,
                        "state_code": data.get("state_code", "WA"),
                        "graduation_year": data.get("graduation_year", 2028),
                        "target_test_date": data.get("target_test_date", ""),
                        "student_name": "Alex"
                    })
                return {"status": "success", "data": data}
            elif resp.get("status") == "not_found":
                # Create on the fly via save_student_profile MCP tool
                default_name = "Alex" if student_id == "student_001" else "Student"
                call_mcp_tool("save_student_profile", {
                    "student_id": student_id,
                    "state_code": "WA",
                    "graduation_year": 2028,
                    "target_test_date": "",
                    "student_name": default_name
                })
                # Re-fetch
                resp_str = call_mcp_tool("fetch_student_profile", {"student_id": student_id})
                resp = json.loads(resp_str)
                if resp.get("status") == "success":
                    return {"status": "success", "data": resp.get("data")}
            return {"status": "error", "message": resp.get("message", "Could not fetch or create student profile.")}
        except Exception as e:
            return {"status": "error", "message": f"Database Service Error: {str(e)}"}

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
            resp_str = call_mcp_tool("log_student_scores", {
                "student_id": student_id,
                "math_score": math_score,
                "rw_score": rw_score,
                "date_test_taken": sanitize_input_string(date_test_taken)
            })
            if resp_str.startswith("Success"):
                return {"status": "success", "message": resp_str}
            return {"status": "error", "message": resp_str}
        except Exception as e:
            return {"status": "error", "message": f"Service Connection Error: The score logging service is currently offline. Details: {str(e)}"}

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
                
                agent = StrategyEngine()
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
                    "pacing_strategy": pacing_strategy,
                    "target_test_date": db_test_date
                }
            }

        except Exception as e:
            return {"status": "error", "message": f"Analytics Database Error: {str(e)}"}

    elif action_type == "GET_SUMMARIES":
        rate_err = _check_rate_limit(student_id, "GET_SUMMARIES")
        if rate_err:
            return rate_err

        state_code = payload.get("state_code", "WA")
        target_test_date = payload.get("target_test_date")
        pacing_strategy = payload.get("pacing_strategy", "")
        summary_type = payload.get("summary_type")

        # Load profile settings via MCP tool for narrator context
        grad_year = 2028
        student_name = "Student"
        try:
            import json
            resp_str = call_mcp_tool("fetch_student_profile", {"student_id": student_id})
            resp = json.loads(resp_str)
            if resp.get("status") == "success":
                profile_data = resp.get("data", {})
                grad_year = profile_data.get("graduation_year", 2028)
                student_name = profile_data.get("student_name", "Student")
        except Exception as e:
            print(f"DEBUG: Failed to read student profile via MCP for summaries: {str(e)}")

        # Calculate days until test
        days_until_test = None
        if target_test_date:
            try:
                test_date = datetime.strptime(target_test_date, "%Y-%m-%d").date()
                days_until_test = (test_date - datetime.now().date()).days
                if days_until_test < 0:
                    days_until_test = 0
            except Exception:
                pass

        # Fetch mastered skills and compute last/next per domain
        mastered_skills = []
        last_mastered_math = None
        next_math = None
        last_mastered_rw = None
        next_rw = None
        mastered_count = 0
        total_skills = 0
        try:
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(DB_PATH)
            conn.row_factory = _sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT topic FROM syllabus_progress WHERE student_id = ? AND is_completed = 1",
                (student_id,)
            )
            mastered_skills = [row["topic"] for row in c.fetchall()]
            conn.close()
            mastered_count = len(mastered_skills)

            # Load ordered skill lists from the syllabus JSON files
            from agents.skills.curriculum_mapper.scheduler_skill import generate_schedule
            import json as _json, os as _os
            _skill_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "agents", "skills", "curriculum_mapper")

            def _ordered_skills(filename):
                try:
                    with open(_os.path.join(_skill_dir, filename)) as f:
                        syllabus = _json.load(f)
                    skills = []
                    for unit in syllabus.get("units", []):
                        domain = unit.get("domain")
                        for topic in unit.get("topics", []):
                            topic_name = topic.get("name")
                            for skill in topic.get("granular_skills", []):
                                skills.append(f"{domain}: {topic_name} - {skill}")
                    return skills
                except Exception:
                    return []

            math_skills = _ordered_skills("math_granular_syllabus.json")
            rw_skills   = _ordered_skills("rw_granular_syllabus.json")
            total_skills = len(math_skills) + len(rw_skills)

            mastered_set = set(mastered_skills)
            math_mastered = [s for s in math_skills if s in mastered_set]
            math_remaining = [s for s in math_skills if s not in mastered_set]
            last_mastered_math = math_mastered[-1] if math_mastered else None
            next_math = math_remaining[0] if math_remaining else None

            rw_mastered = [s for s in rw_skills if s in mastered_set]
            rw_remaining = [s for s in rw_skills if s not in mastered_set]
            last_mastered_rw = rw_mastered[-1] if rw_mastered else None
            next_rw = rw_remaining[0] if rw_remaining else None

        except Exception as e:
            print(f"DEBUG: Failed to fetch mastered skills for narrator: {str(e)}")

        try:
            narrator = NarratorAgent()
            if summary_type == "schedule":
                res = narrator.generate_schedule_summary(
                    state_code, target_test_date, pacing_strategy,
                    grad_year, days_until_test, student_name,
                    mastered_count=mastered_count, total_skills=total_skills
                )
                return {"status": "success", "data": {"schedule_summary": res}}
            elif summary_type == "math":
                res = narrator.generate_math_summary(
                    student_name=student_name,
                    last_mastered_math=last_mastered_math,
                    next_math=next_math,
                )
                return {"status": "success", "data": {"math_summary": res}}
            elif summary_type == "rw":
                res = narrator.generate_rw_summary(
                    student_name=student_name,
                    last_mastered_rw=last_mastered_rw,
                    next_rw=next_rw,
                )
                return {"status": "success", "data": {"rw_summary": res}}
            elif summary_type == "tutor":
                res = narrator.generate_tutor_summary(
                    student_name=student_name,
                    days_until_test=days_until_test,
                )
                return {"status": "success", "data": {"tutor_summary": res}}
            else:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    f_sched = executor.submit(
                        narrator.generate_schedule_summary,
                        state_code, target_test_date, pacing_strategy,
                        grad_year, days_until_test, student_name,
                        mastered_count, total_skills
                    )
                    f_math = executor.submit(
                        narrator.generate_math_summary,
                        student_name, last_mastered_math, next_math
                    )
                    f_rw = executor.submit(
                        narrator.generate_rw_summary,
                        student_name, last_mastered_rw, next_rw
                    )
                    f_tutor = executor.submit(
                        narrator.generate_tutor_summary,
                        student_name, days_until_test
                    )
                    schedule_summary = f_sched.result()
                    math_summary     = f_math.result()
                    rw_summary       = f_rw.result()
                    tutor_summary    = f_tutor.result()
                return {
                    "status": "success",
                    "data": {
                        "schedule_summary": schedule_summary,
                        "math_summary": math_summary,
                        "rw_summary": rw_summary,
                        "tutor_summary": tutor_summary,
                    }
                }
        except Exception as e:
            return {"status": "error", "message": f"Summary Generation Error: {str(e)}"}


    elif action_type == "UPDATE_SYLLABUS":
        topic = payload.get("topic")
        is_completed = payload.get("is_completed")

        if not isinstance(topic, str) or is_completed not in [0, 1]:
            return {"status": "error", "message": "Validation Error: Invalid syllabus data."}

        try:
            resp_str = call_mcp_tool("update_syllabus", {
                "student_id": student_id,
                "topic": sanitize_input_string(topic),
                "is_completed": is_completed
            })
            if resp_str.startswith("Success"):
                return {"status": "success"}
            return {"status": "error", "message": resp_str}
        except Exception as e:
            return {"status": "error", "message": f"Service Connection Error: The syllabus update service is currently offline. Details: {str(e)}"}

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
            
            # 1. Fetch Profile (Graduation Year, Target Test Date & State)
            c.execute("SELECT graduation_year, target_test_date, state_code FROM students WHERE student_id = ?", (student_id,))
            profile_row = c.fetchone()
            if not profile_row or not profile_row[0]:
                 conn.close()
                 return {"status": "error", "message": "No profile found. Please save your graduation year first."}
            grad_year = profile_row[0]
            db_test_date = profile_row[1]
            state_code = profile_row[2] if profile_row[2] else "WA"
            
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
            agent = StrategyEngine()
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
        rate_err = _check_rate_limit(student_id, "TUTOR_CHAT")
        if rate_err:
            return rate_err
        tutor = SyllabusTutorAgent()
        message = payload.get("message", "")
        recent_context = payload.get("recent_context", [])
        return {"status": "success", "data": tutor.answer_question(message, recent_context)}

    elif action_type == "EXPAND_TOPIC":
        rate_err = _check_rate_limit(student_id, "EXPAND_TOPIC")
        if rate_err:
            return rate_err
        expander = TopicExpanderAgent()
        topic_name = payload.get("topic_name", "")
        category = payload.get("category", None)
        
        # Load profile settings from DB
        grad_year = 2028
        test_date = ""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT graduation_year, target_test_date FROM students WHERE student_id = ?", (student_id,))
            row = c.fetchone()
            conn.close()
            if row:
                grad_year = row[0]
                test_date = row[1]
        except Exception as e:
            print(f"DEBUG: Failed to read student profile for topic expander: {str(e)}")
            
        return {"status": "success", "data": expander.expand_topic(topic_name, category, grad_year, test_date)}

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


    elif action_type == "AUTHENTICATE":
        student_id_val = payload.get("student_id", "").strip()
        pin = payload.get("pin", "").strip()
        if not student_id_val or not pin:
            return {"status": "error", "message": "Student ID and PIN are required."}

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT pin_hash FROM student_credentials WHERE student_id = ?", (student_id_val,))
            row = c.fetchone()
            conn.close()
            if row and _verify_pin(pin, row[0], student_id_val):
                session_token = secrets.token_hex(32)
                return {"status": "success", "data": {"session_token": session_token}}
            return {"status": "error", "message": "Invalid Student ID or PIN."}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    elif action_type == "REGISTER_STUDENT":
        student_id_val = payload.get("student_id", "").strip()
        pin = payload.get("pin", "").strip()
        state_code = payload.get("state_code", "WA")
        grad_year = payload.get("graduation_year", 2028)
        target_test_date = payload.get("target_test_date", "")
        student_name = payload.get("student_name", "").strip() or student_id_val

        if not student_id_val or not pin:
            return {"status": "error", "message": "Student ID and PIN are required."}

        # Check target test date rule: must be <= Dec 1 of the year before graduation
        if target_test_date:
            date_error = _validate_test_date(target_test_date, grad_year)
            if date_error:
                return {"status": "error", "message": date_error}

        pin_hash = _hash_pin(pin)

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM student_credentials WHERE student_id = ?", (student_id_val,))
            if c.fetchone():
                conn.close()
                return {"status": "error", "message": "Student ID already exists. Please choose a different one."}
            c.execute("INSERT INTO student_credentials (student_id, pin_hash) VALUES (?, ?)", (student_id_val, pin_hash))
            conn.commit()
            conn.close()

            call_mcp_tool("save_student_profile", {
                "student_id": student_id_val,
                "state_code": sanitize_input_string(state_code),
                "graduation_year": grad_year,
                "target_test_date": sanitize_input_string(target_test_date),
                "student_name": sanitize_input_string(student_name)
            })

            session_token = secrets.token_hex(32)
            return {"status": "success", "data": {"session_token": session_token}}
        except Exception as e:
            return {"status": "error", "message": f"Database Error: {str(e)}"}

    # ==========================================
    # AUTHENTICATE_GUEST: Ephemeral sandbox session
    # Seeds a temporary 11th-grade profile + mock scores so
    # the StrategyEngine can function immediately.
    # TEARDOWN_GUEST removes every trace on logout.
    # ==========================================
    elif action_type == "AUTHENTICATE_GUEST":
        guest_id = "guest_demo"
        today = date.today()
        current_year = today.year
        # 11th grader: graduates next calendar year
        grad_year = current_year + 1
        # Mock test date ~6 months out
        test_date = (today.replace(month=today.month + 6) if today.month <= 6
                     else today.replace(year=today.year + 1, month=today.month - 6)
                     ).strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            # Wipe any stale prior guest session (idempotent)
            for sql in [
                "DELETE FROM syllabus_progress WHERE student_id = ?",
                "DELETE FROM practice_scores WHERE student_id = ?",
                "DELETE FROM students WHERE student_id = ?",
                "DELETE FROM student_credentials WHERE student_id = ?",
            ]:
                c.execute(sql, (guest_id,))

            # Ephemeral bcrypt credentials (PIN is random, never exposed)
            ephemeral_pin = secrets.token_hex(16)
            c.execute(
                "INSERT INTO student_credentials (student_id, pin_hash) VALUES (?, ?)",
                (guest_id, _hash_pin(ephemeral_pin))
            )
            # Standard 11th-grade profile (WA, Primary SAT Year pacing)
            c.execute(
                "INSERT INTO students (student_id, state_code, graduation_year, target_test_date, student_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (guest_id, "WA", grad_year, test_date, "Demo Student")
            )
            # Seed one mock score so the StrategyEngine focus label is non-trivial
            c.execute(
                "INSERT INTO practice_scores (student_id, date_test_taken, sat_total_score, math_score, reading_writing_score) "
                "VALUES (?, ?, ?, ?, ?)",
                (guest_id, today.strftime("%Y-%m-%d"), 1150, 580, 570)
            )
            conn.commit()
            conn.close()

            session_token = secrets.token_hex(32)
            return {"status": "success", "data": {"session_token": session_token}}
        except Exception as e:
            return {"status": "error", "message": f"Guest initialization failed: {str(e)}"}

    elif action_type == "TEARDOWN_GUEST":
        # Hard-coded guard: this action may ONLY target guest_demo
        if student_id != "guest_demo":
            return {"status": "error", "message": "Security Alert: TEARDOWN_GUEST can only target guest_demo."}
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for sql in [
                "DELETE FROM syllabus_progress WHERE student_id = ?",
                "DELETE FROM practice_scores WHERE student_id = ?",
                "DELETE FROM students WHERE student_id = ?",
                "DELETE FROM student_credentials WHERE student_id = ?",
            ]:
                c.execute(sql, (student_id,))
            conn.commit()
            conn.close()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": f"Guest teardown failed: {str(e)}"}

    return {"status": "error", "message": "Security Alert: Unknown action type."}