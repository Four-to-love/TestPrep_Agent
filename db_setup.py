# db_setup.py
# Bootstrap script for fresh environments.
# Run once: python3 db_setup.py
# All tables are idempotent (CREATE TABLE IF NOT EXISTS).
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_state.db")

def create_database():
    print("Building the Zero-Trust Database Schema...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Core Student Profile
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id       TEXT PRIMARY KEY,
            state_code       TEXT,
            graduation_year  INTEGER,
            target_test_date TEXT,
            student_name     TEXT DEFAULT 'Student'
        )
    ''')

    # 2. Testing History (for adaptive score weighting)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id            TEXT,
            date_test_taken       TEXT,
            sat_total_score       INTEGER,
            math_score            INTEGER,
            reading_writing_score INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    # 3. Dynamic Syllabus Progress (for the timeline mastery filter)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS syllabus_progress (
            student_id   TEXT,
            topic        TEXT,
            is_completed INTEGER,
            PRIMARY KEY (student_id, topic),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    # 4. Auth credentials (bcrypt hashed PINs, per-user salt)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_credentials (
            student_id TEXT PRIMARY KEY,
            pin_hash   TEXT
        )
    ''')

    # 5. Topic expansion cache (keyed by topic + grade cohort + weeks remaining)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS topic_expansions_composite (
            topic_name         TEXT,
            graduation_year    INTEGER,
            weeks_remaining    INTEGER,
            expansion_markdown TEXT,
            PRIMARY KEY (topic_name, graduation_year, weeks_remaining)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Success! Database schema ready at {DB_PATH}")

if __name__ == '__main__':
    create_database()