# db_setup.py
import sqlite3

DB_PATH = 'student_state.db'

def create_database():
    print("Building the Zero-Trust Database Schema...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Core Student Profile
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            state_code TEXT,
            graduation_year INTEGER
        )
    ''')

    # 2. Testing History (For adaptive weighting)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            date_test_taken TEXT,
            sat_total_score INTEGER,
            math_score INTEGER,
            reading_writing_score INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    # 3. Dynamic Syllabus Progress (For the timeline filter)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS syllabus_progress (
            student_id TEXT,
            topic TEXT,
            is_completed INTEGER,
            PRIMARY KEY (student_id, topic),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Success! Database locked and loaded at {DB_PATH}")

if __name__ == '__main__':
    create_database()