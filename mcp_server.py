import sqlite3
import os
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TestPrep Score Checker", host="0.0.0.0", port=8000)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_state.db")

@mcp.tool()
def fetch_score_history(student_id: str) -> str:
    """Fetch structured, chronological list of past Math and RW scores for a student.

    Args:
        student_id: The string ID of the student (e.g. 'student_001' or 'guest_demo').
    """
    if not student_id or not isinstance(student_id, str) or not student_id.strip():
        return "Error: Validation Failed. student_id must be a non-empty string."

    if not os.path.exists(DB_PATH):
        return f"Error: Database file not found at {DB_PATH}"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT date_test_taken, math_score, reading_writing_score, sat_total_score
            FROM practice_scores
            WHERE student_id = ?
            ORDER BY id ASC
        ''', (student_id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return f"No score history found for student {student_id}."

        history = []
        for row in rows:
            history.append({
                "date": row["date_test_taken"],
                "math": row["math_score"],
                "rw": row["reading_writing_score"],
                "total": row["sat_total_score"]
            })
        return json.dumps(history, indent=2)
    except Exception as e:
        return f"Database Error: {str(e)}"

@mcp.tool()
def log_student_scores(student_id: str, math_score: int, rw_score: int, date_test_taken: str) -> str:
    """Log a new set of practice SAT scores for a student.

    Args:
        student_id: The string ID of the student.
        math_score: Math score (160 to 800).
        rw_score: Reading & Writing score (160 to 800).
        date_test_taken: YYYY-MM-DD format date of the test.
    """
    if not student_id or not isinstance(student_id, str) or not student_id.strip():
        return "Error: Validation Failed. student_id must be a non-empty string."

    try:
        math_score = int(math_score)
        rw_score = int(rw_score)
    except (ValueError, TypeError):
        return "Error: Validation Failed. Scores must be valid integers."

    if not (160 <= math_score <= 800) or not (160 <= rw_score <= 800):
        return "Error: Scores must be between 160 and 800."

    sat_total = math_score + rw_score

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO practice_scores (student_id, date_test_taken, sat_total_score, math_score, reading_writing_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, date_test_taken, sat_total, math_score, rw_score))
        conn.commit()
        conn.close()
        return "Success: Scores logged successfully."
    except Exception as e:
        return f"Database Error: {str(e)}"


@mcp.tool()
def save_student_profile(student_id: str, state_code: str, graduation_year: int, target_test_date: str, student_name: str) -> str:
    """Save or update a student's profile information.
    
    Args:
        student_id: The ID of the student.
        state_code: Two-letter US state code.
        graduation_year: High school graduation year.
        target_test_date: YYYY-MM-DD format target test date.
        student_name: Full name of the student.
    """
    try:
        graduation_year = int(graduation_year)
    except (ValueError, TypeError):
        return "Error: Validation Failed. Graduation year must be a valid integer."
        
    try:
        if str(student_id).isdigit():
            db_student_id = f"student_{int(student_id):03d}"
        else:
            db_student_id = str(student_id).strip()
    except Exception:
        db_student_id = str(student_id).strip()

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if student exists
        c.execute("SELECT 1 FROM students WHERE student_id = ?", (db_student_id,))
        if c.fetchone():
            c.execute('''
                UPDATE students 
                SET state_code = ?, graduation_year = ?, target_test_date = ?, student_name = ?
                WHERE student_id = ?
            ''', (state_code, graduation_year, target_test_date, student_name, db_student_id))
        else:
            c.execute('''
                INSERT INTO students (student_id, state_code, graduation_year, target_test_date, student_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (db_student_id, state_code, graduation_year, target_test_date, student_name))
            
        conn.commit()
        conn.close()
        return "Success: Profile saved successfully."
    except Exception as e:
        return f"Database Error: {str(e)}"


@mcp.tool()
def fetch_student_profile(student_id: str) -> str:
    """Fetch a student's profile settings (name, state, grad year, test date).
    
    Args:
        student_id: The ID of the student.
    """
    try:
        if str(student_id).isdigit():
            db_student_id = f"student_{int(student_id):03d}"
        else:
            db_student_id = str(student_id).strip()
    except Exception:
        db_student_id = str(student_id).strip()
        
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT state_code, graduation_year, target_test_date, student_name FROM students WHERE student_id = ?", (db_student_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.dumps({
                "status": "success",
                "data": {
                    "state_code": row["state_code"],
                    "graduation_year": row["graduation_year"],
                    "target_test_date": row["target_test_date"],
                    "student_name": row["student_name"]
                }
            })
        return json.dumps({"status": "not_found"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool()
def update_syllabus(student_id: str, topic: str, is_completed: int) -> str:
    """Update progress tracking for a syllabus topic.

    Args:
        student_id: The string ID of the student.
        topic: Full syllabus topic name.
        is_completed: 1 for completed/mastered, 0 for incomplete.
    """
    if not student_id or not isinstance(student_id, str) or not student_id.strip():
        return "Error: Validation Failed. student_id must be a non-empty string."

    try:
        is_completed = int(is_completed)
    except (ValueError, TypeError):
        return "Error: Validation Failed. is_completed must be 0 or 1."

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM syllabus_progress WHERE student_id = ? AND topic = ?", (student_id, topic))
        if is_completed == 1:
            c.execute('''
                INSERT INTO syllabus_progress (student_id, topic, is_completed)
                VALUES (?, ?, 1)
            ''', (student_id, topic))
        conn.commit()
        conn.close()
        return "Success: Syllabus progress updated."
    except Exception as e:
        return f"Database Error: {str(e)}"

@mcp.tool()
def get_cached_topic_expansion(topic_name: str, graduation_year: int, weeks_remaining: int) -> str:
    """Retrieve cached topic expansion from the database.
    
    Args:
        topic_name: The name of the syllabus topic.
        graduation_year: High school graduation year of the student.
        weeks_remaining: Number of weeks remaining until the target test date.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS topic_expansions_composite (
                topic_name TEXT,
                graduation_year INTEGER,
                weeks_remaining INTEGER,
                expansion_markdown TEXT,
                PRIMARY KEY (topic_name, graduation_year, weeks_remaining)
            )
        ''')
        conn.commit()
        
        c.execute('''
            SELECT expansion_markdown FROM topic_expansions_composite
            WHERE topic_name = ? AND graduation_year = ? AND weeks_remaining = ?
        ''', (topic_name, int(graduation_year), int(weeks_remaining)))
        row = c.fetchone()
        conn.close()
        if row:
            return json.dumps({"status": "found", "data": row[0]})
        return json.dumps({"status": "not_found"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

@mcp.tool()
def save_topic_expansion(topic_name: str, graduation_year: int, weeks_remaining: int, expansion_markdown: str) -> str:
    """Cache a generated topic expansion in the database.
    
    Args:
        topic_name: The name of the syllabus topic.
        graduation_year: High school graduation year of the student.
        weeks_remaining: Number of weeks remaining until the target test date.
        expansion_markdown: The markdown content of the topic expansion card.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS topic_expansions_composite (
                topic_name TEXT,
                graduation_year INTEGER,
                weeks_remaining INTEGER,
                expansion_markdown TEXT,
                PRIMARY KEY (topic_name, graduation_year, weeks_remaining)
            )
        ''')
        conn.commit()
        
        c.execute('''
            INSERT OR REPLACE INTO topic_expansions_composite (topic_name, graduation_year, weeks_remaining, expansion_markdown)
            VALUES (?, ?, ?, ?)
        ''', (topic_name, int(graduation_year), int(weeks_remaining), expansion_markdown))
        conn.commit()
        conn.close()
        return "Success: Expansion cached."
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse")
