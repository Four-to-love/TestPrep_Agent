import sqlite3
import json
import os

# Set absolute paths so the server always finds the data
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR_PATH, "student_state.db")
KB_PATH = os.path.join(DIR_PATH, "knowledge_base", "rag_store.json")

class TestPrepMCPServer:
    """
    Model Context Protocol (MCP) Server.
    This acts as the ONLY authorized bridge between the AI Agents and the raw data.
    """
    
    @staticmethod
    def get_merit_threshold(state_code, class_year):
        """
        Tool 1: Fetches the National Merit threshold. 
        Intelligently falls back to the latest projection for future years.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # The Magic Query: Get the closest year less than or equal to the requested year
            c.execute('''
                SELECT class_year, selection_index, is_projection 
                FROM merit_thresholds 
                WHERE state_code = ? AND class_year <= ?
                ORDER BY class_year DESC
                LIMIT 1
            ''', (state_code.upper(), class_year))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                found_year, score, is_proj = result
                status = "projected" if is_proj else "official"
                
                # If we found the exact year requested
                if found_year == class_year:
                    return f"The {status} National Merit cutoff for {state_code.upper()} in {class_year} is {score}."
                # If we had to fall back to an earlier projection for a future year
                else:
                    return f"Data for {class_year} is not yet available. Using the latest {status} baseline from {found_year}, the estimated cutoff for {state_code.upper()} is {score}."
            else:
                return f"No threshold data found for {state_code.upper()}."
        except Exception as e:
            return f"Database error: {str(e)}"
            
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

if __name__ == "__main__":
    server = TestPrepMCPServer()
    print("--- Testing Forward-Compatible MCP Server ---")
    
    print("\n1. Testing Exact Year (2026):")
    print(server.get_merit_threshold("WA", 2026))
    
    print("\n2. Testing Future Year (2029) Fallback Logic:")
    print(server.get_merit_threshold("CA", 2029))