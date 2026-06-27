import json
import sqlite3
from datetime import date
import os
from dotenv import load_dotenv
from agents import StrategistAgent

# Load environment variables from the .env file securely
load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY environment variable is not set!")
    print("Please ensure your .env file contains: GEMINI_API_KEY='your_actual_key'")

def setup_test_data(student_id, state, grad_year):
    """Injects a test student and dummy scores into the SQLite DB."""
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()
    
    # Ensure tables exist (including the new syllabus_progress table)
    c.execute('''CREATE TABLE IF NOT EXISTS students (student_id TEXT PRIMARY KEY, pin_hash TEXT, state_code TEXT, graduation_year INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS practice_scores (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, test_date TEXT, sat_total_score INTEGER, math_score INTEGER, reading_writing_score INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS syllabus_progress (student_id TEXT, topic TEXT, is_completed INTEGER, PRIMARY KEY (student_id, topic))''')
    
    # Insert dummy student
    c.execute("REPLACE INTO students (student_id, pin_hash, state_code, graduation_year) VALUES (?, ?, ?, ?)", 
              (student_id, "dummy_hash", state, grad_year))
    
    # Add some dummy scores so the agent can analyze gaps
    c.execute("SELECT COUNT(*) FROM practice_scores WHERE student_id = ?", (student_id,))
    if c.fetchone()[0] == 0:
        print("📊 Seeding database with dummy test scores (Weak in Math: 600, Strong in R/W: 720)...")
        c.execute('''INSERT INTO practice_scores (student_id, test_date, sat_total_score, math_score, reading_writing_score)
                     VALUES (?, ?, ?, ?, ?)''', (student_id, str(date.today()), 1320, 600, 720)) 
        conn.commit()
    conn.close()

def run_test():
    test_id = "crunch_time_junior"
    test_state = "TX"
    test_year = 2027 # 11th grader for the 2026-2027 school year

    print(f"--- Setting up test environment for {test_id} ---")
    setup_test_data(test_id, test_state, test_year)

    print(f"\n--- Initializing TestPrep_Agent ---")
    print(f"Student: {test_id} | Class of {test_year} | State: {test_state}")
    
    agent = StrategistAgent(
        student_id=test_id,
        state_code=test_state,
        class_year=test_year
    )

    print("\n--- Requesting 6-Week Schedule from Gemini API (Please wait...) ---")
    # Overriding the prompt slightly for this test to force the 6-week timeline
    hardcoded_prompt = "Execute timeline calculation, assume the student takes the test in exactly 6 weeks. Spread the Khan Academy curriculum across these 6 weeks and generate the JSON schedule."
    
    try:
        # Access the internal chat object to pass the custom test prompt
        chat = agent.client.chats.create(model="gemini-2.5-flash", config=agent.config)
        response = chat.send_message(hardcoded_prompt)
        
        # Clean up the response in case the model added markdown formatting
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        plan = json.loads(raw_text.strip())
        print("\n--- Final Agent Output ---")
        print(json.dumps(plan, indent=4))

    except Exception as e:
        print(f"\nError running test: {e}")

if __name__ == "__main__":
    run_test()