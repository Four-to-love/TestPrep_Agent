import sqlite3
import json
import os
from datetime import datetime, date
import json
from constants import STATE_CUTOFFS  # Import the single source of truth

# Set absolute paths so the server always finds the data
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR_PATH, "student_state.db")
KB_PATH = os.path.join(DIR_PATH, "knowledge_base", "rag_store.json")

class TestPrepMCPServer:
    """
    Model Context Protocol (MCP) Server.
    The ONLY authorized bridge between the AI Agents and the raw data.
    """
    
    @staticmethod
    def get_merit_threshold(self, state_code: str, class_year: int = None) -> str:
        """
        MCP Tool: Fetches the National Merit threshold for a given state.
        Now reads from the centralized constants.py file.
        """
        target = STATE_CUTOFFS.get(state_code.upper(), 220)
        return f"The National Merit Selection Index threshold for {state_code.upper()} is currently {target}."

            
    @staticmethod
    def search_knowledge_base(topic_keyword):
        """Tool 2: Retrieves academic strategies from the JSON semantic brain."""
        try:
            with open(KB_PATH, "r") as f:
                kb = json.load(f)
                
            results = [
                fact["content"] for fact in kb["facts"] 
                if topic_keyword.lower() in fact["topic"].lower() or topic_keyword.lower() in fact["content"].lower()
            ]
            
            if results:
                return " | ".join(results)
            return "No relevant guidelines found in the Knowledge Base."
        except FileNotFoundError:
            return "Error: Knowledge Base file not found. Run ingestion script first."

    @staticmethod
    def get_student_scores(student_id):
        """Tool 3: Retrieves a specific student's past practice scores safely."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                SELECT test_date, sat_total_score, math_score, reading_writing_score 
                FROM practice_scores 
                WHERE student_id = ? 
                ORDER BY test_date ASC
            ''', (student_id,))
            results = c.fetchall()
            conn.close()
            
            if results:
                history = [f"Date: {r[0]}, Total: {r[1]} (Math: {r[2]}, RW: {r[3]})" for r in results]
                return "\n".join(history)
            return "No practice scores logged yet."
        except Exception as e:
            return f"Database error: {str(e)}"

    @staticmethod
    def Skill_Fetch_Academic_Timeline(class_year, target_month_year=None):
        """
        Tool 4: Calculates exact weeks remaining.
        Accepts an optional user-defined target_month_year (format: "YYYY-MM").
        Calculates all deadlines based on the 1st of the month.
        """
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        years_to_grad = class_year - current_year
        if current_month >= 8:
            years_to_grad -= 1
        
        grade = 12 - years_to_grad
        
        target_date = None
        milestone = ""
        urgency = ""
        
        # If the user explicitly provided a test date, override the default logic
        if target_month_year:
            try:
                t_year, t_month = map(int, target_month_year.split("-"))
                target_date = date(t_year, t_month, 1)  # Anchored to the 1st
                milestone = f"User-Selected Target ({target_date.strftime('%B %Y')})"
                urgency = "Custom Pacing"
                
                if now.date() > target_date:
                    return {"status": "Error: The selected test date is in the past."}
            except ValueError:
                return {"error": "Invalid date format. Expected YYYY-MM."}
                
        # Otherwise, fall back to the dynamic grade logic
        else:
            if grade <= 10:
                target_year = class_year - 2 
                target_date = date(target_year, 10, 1) # Changed to the 1st
                
                if now.date() > target_date:
                    target_year = class_year - 1
                    target_date = date(target_year, 3, 1) # Changed to the 1st
                    milestone = "First Official SAT (Spring 11th Grade)"
                    urgency = "Medium (Active Preparation)"
                else:
                    milestone = "PSAT (Fall 10th Grade)"
                    urgency = "Low (Foundational Phase)"
                    
            elif grade == 11:
                target_year = class_year - 1
                target_date = date(target_year, 3, 1) # Changed to the 1st
                
                if now.date() > target_date:
                    target_year = class_year
                    target_date = date(target_year, 10, 1) # Changed to the 1st
                    milestone = "Final SAT Retakes (Fall 12th Grade)"
                    urgency = "High (Acceleration Protocol)"
                else:
                    milestone = "First Official SAT (Spring 11th Grade)"
                    urgency = "High (Active Preparation)"
                    
            else:
                return {"status": "Testing window closed or closing. Focus on college applications."}

        # Calculate exact weeks remaining
        delta = target_date - now.date()
        weeks_remaining = max(0, delta.days // 7)
        
        return {
            "current_grade": grade,
            "next_milestone": milestone,
            "target_date": str(target_date),
            "weeks_remaining": weeks_remaining,
            "urgency_level": urgency
        }

    @staticmethod
    def Skill_Analyze_Performance_Gaps(student_id):
        """Tool 5: Pulls historical practice scores to identify weakest domains."""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                SELECT test_date, sat_total_score, math_score, reading_writing_score
                FROM practice_scores
                WHERE student_id = ?
                ORDER BY test_date ASC
            ''', (student_id,))
            results = c.fetchall()
            conn.close()

            if not results:
                return {"status": "No practice scores logged yet. Cannot analyze gaps."}

            if len(results) == 1:
                r = results[0]
                weakest = "Math" if r[2] < r[3] else "Reading/Writing"
                return {
                    "status": "Baseline established. Need more tests for trend analysis.",
                    "latest_total": r[1],
                    "weakest_domain": weakest,
                    "math_score": r[2],
                    "rw_score": r[3]
                }

            first_test = results[0]
            latest_test = results[-1]

            total_delta = latest_test[1] - first_test[1]
            math_delta = latest_test[2] - first_test[2]
            rw_delta = latest_test[3] - first_test[3]

            weakest = "Math" if latest_test[2] < latest_test[3] else "Reading/Writing"

            return {
                "status": "Trend analysis complete.",
                "tests_taken": len(results),
                "latest_total": latest_test[1],
                "total_improvement": total_delta,
                "weakest_domain": weakest,
                "domain_deltas": {
                    "math_improvement": math_delta,
                    "reading_writing_improvement": rw_delta
                }
            }
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

if __name__ == "__main__":
    server = TestPrepMCPServer()
    print("--- Testing Updated Timeline Logic ---")
    
    print("\n1. Testing Default Logic (No Date Provided):")
    default_result = server.Skill_Fetch_Academic_Timeline(2028)
    print(json.dumps(default_result, indent=2))
    
    print("\n2. Testing User-Selected Override (August 2026):")
    override_result = server.Skill_Fetch_Academic_Timeline(2028, "2026-08")
    print(json.dumps(override_result, indent=2))