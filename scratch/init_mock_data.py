import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../student_state.db")

def init_mock_students():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Inject 3 Students
    students_data = [
        ("student_001", "WA", 2028, "2026-10-04"),
        ("student_002", "CA", 2027, "2026-11-05"),
        ("student_003", "NY", 2026, "2026-12-06")
    ]
    for sid, state, grad_yr, test_date in students_data:
        c.execute('''
            INSERT OR REPLACE INTO students (student_id, state_code, graduation_year, target_test_date)
            VALUES (?, ?, ?, ?)
        ''', (sid, state, grad_yr, test_date))
        
    # 2. Inject Chronological Practice Scores
    scores_data = [
        # Student 001
        ("student_001", "2026-04-10", 1000, 500, 500),
        ("student_001", "2026-05-12", 1100, 550, 550),
        ("student_001", "2026-06-15", 1180, 600, 580),
        # Student 002
        ("student_002", "2026-04-15", 1200, 600, 600),
        ("student_002", "2026-05-20", 1280, 640, 640),
        ("student_002", "2026-06-18", 1350, 680, 670),
        # Student 003
        ("student_003", "2026-04-20", 1400, 700, 700),
        ("student_003", "2026-05-25", 1480, 730, 750),
        ("student_003", "2026-06-22", 1540, 770, 770),
    ]
    
    # Clean old scores to prevent duplicates
    c.execute("DELETE FROM practice_scores")
    
    for sid, date_taken, total, math, rw in scores_data:
        c.execute('''
            INSERT INTO practice_scores (student_id, date_test_taken, sat_total_score, math_score, reading_writing_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (sid, date_taken, total, math, rw))
        
    conn.commit()
    conn.close()
    print("Mock database populated successfully!")

if __name__ == "__main__":
    init_mock_students()
