import json
import sqlite3
from datetime import date
import os
from agents import StrategistAgent

# Ensure your API key is loaded if it's not set in the terminal session
# If you exported it previously, this just passes through safely.
if not os.environ.get("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY environment variable is not set!")
    print("Run: export GEMINI_API_KEY='your_key' before running this test.")

def setup_test_data(student_id, state, grad_year):
    """Injects a test student and dummy scores into the SQLite DB."""
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()
    
    # Ensure tables exist
    c.execute('''CREATE TABLE IF NOT EXISTS students (student_id TEXT PRIMARY KEY, pin_hash TEXT, state_code TEXT, graduation_year INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS practice_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, test_date TEXT, sat_total_score INTEGER, math_score INTEGER, reading_writing_score INTEGER)''')
    
    # Insert dummy student (using REPLACE to avoid errors on multiple runs)
    c.execute("REPLACE INTO students (student_id, pin_hash, state_code, graduation_year) VALUES (?, ?, ?, ?)", 
              (student_id, "dummy_hash", state, grad_year))
    
    # Check if scores exist, if not, add some
    c.execute("SELECT COUNT(*) FROM practice_scores WHERE student_id = ?", (student_id,))
    if c.fetchone()[0] == 0:
        print("📊 Seeding database with dummy test scores (Weak in Math: 600, Strong in R/W: 720)...")
        c.execute('''INSERT INTO practice_scores (student_id, test_date, sat_total_score, math_score, reading_writing_score)
                     VALUES (?, ?, ?, ?, ?)''', (student_id, str(date.today()), 1320, 600, 720)) 
        conn.commit()
    conn.close()

def run_test():
    test_id = "demo_student_99"
    test_state = "TX"
    test_year = 2028 # 10th grader

    print(f"--- Setting up test environment for {test_id} ---")
    setup_test_data(test_id, test_state, test_year)

    print(f"\n--- Initializing TestPrep_Agent ---")
    print(f"Student: {test_id} | Class of {test_year} | State: {test_state}")
    
    agent = StrategistAgent(
        student_id=test_id,
        state_code=test_state,
        class_year=test_year
    )

    print("\n--- Requesting Schedule from Gemini API (Please wait...) ---")
    plan = agent.generate_action_plan()

    print("\n--- Final Agent Output ---")
    # Print the resulting dictionary as nicely formatted JSON
    print(json.dumps(plan, indent=4))

if __name__ == "__main__":
    run_test()