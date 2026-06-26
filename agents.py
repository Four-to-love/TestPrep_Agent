import json
from datetime import datetime
from mcp_server import TestPrepMCPServer

class GatekeeperAgent:
    def __init__(self):
        self.malicious_keywords = [
            "ignore previous", "delete", "drop", "update", 
            "insert", "change my score", "bypass", "system prompt"
        ]

    def evaluate_intent(self, prompt: str) -> tuple[bool, str]:
        """Scans the input for malicious SQL/Database alteration intents."""
        prompt_lower = prompt.lower()
        for word in self.malicious_keywords:
            if word in prompt_lower:
                return False, f"Unauthorized database modification attempt detected ('{word}')."
        return True, ""


class StrategistAgent:
    # UPDATED: Now requires class_year dynamically
    def __init__(self, student_id: str, state_code: str, class_year: int):
        self.student_id = student_id
        self.state_code = state_code
        self.class_year = class_year
        self.mcp = TestPrepMCPServer()

    def calculate_current_grade(self, class_year):
        """Dynamically calculates the student's grade level based on the current date."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        years_to_grad = class_year - current_year
        if current_month >= 8:
            years_to_grad -= 1
            
        calculated_grade = 12 - years_to_grad
        if calculated_grade > 12: return 12
        if calculated_grade < 8: return 8
        return calculated_grade

    def process_query(self, prompt: str):
        """A generator that yields tool execution logs and final text content."""
        # 1. Temporal Calculation using dynamic class_year
        grade = self.calculate_current_grade(self.class_year)
        search_keyword = f"Grade {grade}"
        
        # --- TOOL EXECUTION 1: Fetch Thresholds ---
        yield {
            "type": "tool_call",
            "tool_name": "get_merit_threshold",
            "tool_args": {"state_code": self.state_code, "class_year": self.class_year}
        }
        threshold_data = self.mcp.get_merit_threshold(self.state_code, self.class_year)
        
        # --- TOOL EXECUTION 2: Semantic Brain ---
        yield {
            "type": "tool_call",
            "tool_name": "search_knowledge_base",
            "tool_args": {"topic_keyword": search_keyword}
        }
        pacing_data = self.mcp.search_knowledge_base(search_keyword)
        
        # --- SYNTHESIS ---
        final_response = (
            f"**Trajectory Analysis for Class of {self.class_year} ({self.state_code}):**\n\n"
            f"📊 **Threshold Data:** {threshold_data}\n\n"
            f"📅 **Current Positioning:** Since you are currently in **{search_keyword}**, "
            f"your targeted pacing profile dictates the following:\n\n> {pacing_data}"
        )
        
        yield {
            "type": "content",
            "text": final_response
        }