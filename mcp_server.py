import sqlite3
import os
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TestPrep Score Checker")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_state.db")

@mcp.tool()
def fetch_score_history(student_id: int) -> str:
    """Fetch structured, chronological list of past Math and RW scores for a student.
    
    Args:
        student_id: The ID of the student (must be an integer, e.g. 1).
    """
    # 1. Type-cast and sanitize inputs (Zero-Trust Security)
    try:
        student_id = int(student_id)
    except (ValueError, TypeError):
        return "Error: Validation Failed. student_id must be a valid integer."
        
    # 2. Zero-Trust Verification: Ensure the requested ID matches the active user session context (student_001)
    # The active user is "student_001" (student_id = 1). Other IDs must be denied access.
    if student_id != 1:
        return "Error: Access Denied. The requested student_id does not match the active session context."

    db_student_id = f"student_{student_id:03d}"

    if not os.path.exists(DB_PATH):
        return f"Error: Database file not found at {DB_PATH}"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 3. Secure parameterized query to prevent SQL injection
        c.execute('''
            SELECT date_test_taken, math_score, reading_writing_score, sat_total_score 
            FROM practice_scores 
            WHERE student_id = ? 
            ORDER BY id ASC
        ''', (db_student_id,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return f"No score history found for student {db_student_id}."
            
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
def log_student_scores(student_id: int, math_score: int, rw_score: int, date_test_taken: str) -> str:
    """Log a new set of practice SAT scores for a student.
    
    Args:
        student_id: The ID of the student (must be 1).
        math_score: Math score (160 to 800).
        rw_score: Reading & Writing score (160 to 800).
        date_test_taken: YYYY-MM-DD format date of the test.
    """
    try:
        student_id = int(student_id)
        math_score = int(math_score)
        rw_score = int(rw_score)
    except (ValueError, TypeError):
        return "Error: Validation Failed. Inputs must be valid integers."
        
    if student_id != 1:
        return "Error: Access Denied. Unauthorized student_id."
        
    if not (160 <= math_score <= 800) or not (160 <= rw_score <= 800):
        return "Error: Scores must be between 160 and 800."

    db_student_id = f"student_{student_id:03d}"
    sat_total = math_score + rw_score

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO practice_scores (student_id, date_test_taken, sat_total_score, math_score, reading_writing_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (db_student_id, date_test_taken, sat_total, math_score, rw_score))
        conn.commit()
        conn.close()
        return "Success: Scores logged successfully."
    except Exception as e:
        return f"Database Error: {str(e)}"


@mcp.tool()
def save_student_profile(student_id: int, state_code: str, graduation_year: int, target_test_date: str) -> str:
    """Save or update a student's profile information.
    
    Args:
        student_id: The ID of the student (must be 1).
        state_code: Two-letter US state code.
        graduation_year: High school graduation year.
        target_test_date: YYYY-MM-DD format target test date.
    """
    try:
        student_id = int(student_id)
        graduation_year = int(graduation_year)
    except (ValueError, TypeError):
        return "Error: Validation Failed. Numeric fields must be valid integers."
        
    if student_id != 1:
        return "Error: Access Denied. Unauthorized student_id."
        
    db_student_id = f"student_{student_id:03d}"

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if student exists
        c.execute("SELECT 1 FROM students WHERE student_id = ?", (db_student_id,))
        if c.fetchone():
            c.execute('''
                UPDATE students 
                SET state_code = ?, graduation_year = ?, target_test_date = ?
                WHERE student_id = ?
            ''', (state_code, graduation_year, target_test_date, db_student_id))
        else:
            c.execute('''
                INSERT INTO students (student_id, state_code, graduation_year, target_test_date)
                VALUES (?, ?, ?, ?)
            ''', (db_student_id, state_code, graduation_year, target_test_date))
            
        conn.commit()
        conn.close()
        return "Success: Profile saved successfully."
    except Exception as e:
        return f"Database Error: {str(e)}"


@mcp.tool()
def update_syllabus(student_id: int, topic: str, is_completed: int) -> str:
    """Update progress tracking for a syllabus topic.
    
    Args:
        student_id: The ID of the student (must be 1).
        topic: Full syllabus topic name.
        is_completed: 1 for completed/mastered, 0 for incomplete.
    """
    try:
        student_id = int(student_id)
        is_completed = int(is_completed)
    except (ValueError, TypeError):
        return "Error: Validation Failed. Numeric fields must be valid integers."
        
    if student_id != 1:
        return "Error: Access Denied. Unauthorized student_id."
        
    db_student_id = f"student_{student_id:03d}"

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("DELETE FROM syllabus_progress WHERE student_id = ? AND topic = ?", (db_student_id, topic))
        if is_completed == 1:
            c.execute('''
                INSERT INTO syllabus_progress (student_id, topic, is_completed)
                VALUES (?, ?, 1)
            ''', (db_student_id, topic))
            
        conn.commit()
        conn.close()
        return "Success: Syllabus progress updated."
    except Exception as e:
        return f"Database Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
