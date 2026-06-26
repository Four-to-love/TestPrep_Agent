import sqlite3

def init_db():
    # This creates a local file called 'student_state.db'
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()

    # Create the Student Profile Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            pin_hash TEXT,
            state_code TEXT
        )
    ''')

    # Create the Score Tracking Table (UPDATED SCHEMA)
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            test_date TEXT,
            sat_total_score INTEGER,
            math_score INTEGER,
            reading_writing_score INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Database vault initialized successfully. New schema ready for TestPrep_Agent.")

if __name__ == "__main__":
    init_db()