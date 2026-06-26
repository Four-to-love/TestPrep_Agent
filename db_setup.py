import sqlite3

def init_db():
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()
    
    # 1. Student Profile Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            pin_hash TEXT,
            state_code TEXT
        )
    ''')
    
    # 2. Score Tracking Table
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
    
    # 3. The Deterministic Knowledge Base (Multi-Year Support)
    c.execute('DROP TABLE IF EXISTS merit_thresholds')
    
    c.execute('''
        CREATE TABLE merit_thresholds (
            state_code TEXT,
            class_year INTEGER,
            selection_index INTEGER,
            is_projection BOOLEAN,
            PRIMARY KEY (state_code, class_year)
        )
    ''')
    
    # The Complete 50-State + DC Dataset for 2026 and 2027
    threshold_data = [
        # Class of 2026 (Actuals, is_projection = False)
        ("AL", 2026, 214, False), ("AK", 2026, 215, False), ("AZ", 2026, 218, False),
        ("AR", 2026, 215, False), ("CA", 2026, 224, False), ("CO", 2026, 219, False),
        ("CT", 2026, 223, False), ("DE", 2026, 220, False), ("FL", 2026, 219, False),
        ("GA", 2026, 220, False), ("HI", 2026, 219, False), ("ID", 2026, 215, False),
        ("IL", 2026, 222, False), ("IN", 2026, 218, False), ("IA", 2026, 214, False),
        ("KS", 2026, 216, False), ("KY", 2026, 214, False), ("LA", 2026, 216, False),
        ("ME", 2026, 217, False), ("MD", 2026, 224, False), ("MA", 2026, 225, False),
        ("MI", 2026, 220, False), ("MN", 2026, 219, False), ("MS", 2026, 213, False),
        ("MO", 2026, 217, False), ("MT", 2026, 213, False), ("NE", 2026, 214, False),
        ("NV", 2026, 214, False), ("NH", 2026, 219, False), ("NJ", 2026, 225, False),
        ("NM", 2026, 210, False), ("NY", 2026, 223, False), ("NC", 2026, 220, False),
        ("ND", 2026, 210, False), ("OH", 2026, 219, False), ("OK", 2026, 212, False),
        ("OR", 2026, 219, False), ("PA", 2026, 221, False), ("RI", 2026, 219, False),
        ("SC", 2026, 215, False), ("SD", 2026, 211, False), ("TN", 2026, 219, False),
        ("TX", 2026, 222, False), ("UT", 2026, 213, False), ("VT", 2026, 216, False),
        ("VA", 2026, 224, False), ("WA", 2026, 224, False), ("WV", 2026, 210, False),
        ("WI", 2026, 215, False), ("WY", 2026, 210, False), ("DC", 2026, 225, False),

        # Class of 2027 (Projections based on historical +/- 1 pt shifts, is_projection = True)
        ("AL", 2027, 213, True), ("AK", 2027, 214, True), ("AZ", 2027, 217, True),
        ("AR", 2027, 214, True), ("CA", 2027, 224, True), ("CO", 2027, 218, True),
        ("CT", 2027, 222, True), ("DE", 2027, 219, True), ("FL", 2027, 218, True),
        ("GA", 2027, 219, True), ("HI", 2027, 218, True), ("ID", 2027, 214, True),
        ("IL", 2027, 221, True), ("IN", 2027, 217, True), ("IA", 2027, 213, True),
        ("KS", 2027, 215, True), ("KY", 2027, 213, True), ("LA", 2027, 215, True),
        ("ME", 2027, 216, True), ("MD", 2027, 223, True), ("MA", 2027, 224, True),
        ("MI", 2027, 219, True), ("MN", 2027, 218, True), ("MS", 2027, 212, True),
        ("MO", 2027, 216, True), ("MT", 2027, 212, True), ("NE", 2027, 213, True),
        ("NV", 2027, 213, True), ("NH", 2027, 218, True), ("NJ", 2027, 224, True),
        ("NM", 2027, 210, True), ("NY", 2027, 222, True), ("NC", 2027, 219, True),
        ("ND", 2027, 210, True), ("OH", 2027, 218, True), ("OK", 2027, 211, True),
        ("OR", 2027, 218, True), ("PA", 2027, 220, True), ("RI", 2027, 218, True),
        ("SC", 2027, 214, True), ("SD", 2027, 210, True), ("TN", 2027, 218, True),
        ("TX", 2027, 221, True), ("UT", 2027, 212, True), ("VT", 2027, 215, True),
        ("VA", 2027, 223, True), ("WA", 2027, 223, True), ("WV", 2027, 210, True),
        ("WI", 2027, 214, True), ("WY", 2027, 210, True), ("DC", 2027, 224, True)
    ]
    
    # Insert the massive dataset securely
    c.executemany('''
        INSERT OR REPLACE INTO merit_thresholds (state_code, class_year, selection_index, is_projection) 
        VALUES (?, ?, ?, ?)
    ''', threshold_data)
    
    conn.commit()
    conn.close()
    print(f"Database vault updated! Loaded {len(threshold_data)} National Merit thresholds spanning 2026 and 2027.")

if __name__ == "__main__":
    init_db()