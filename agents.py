import json
from datetime import datetime
from mcp_server import TestPrepMCPServer

class AgentOrchestrator:
    def __init__(self):
        self.mcp = TestPrepMCPServer()
        
    def calculate_current_grade(self, class_year):
        """Dynamically calculates the student's grade level based on the current date."""
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Calculate how many years until graduation
        years_to_grad = class_year - current_year
        
        # Adjust if we are in the second half of the year (new school year starts in August)
        if current_month >= 8:
            years_to_grad -= 1
            
        calculated_grade = 12 - years_to_grad
        
        # Clamp bounds to our supported ecosystem (Grades 8 to 12)
        if calculated_grade > 12: return 12
        if calculated_grade < 8: return 8
        return calculated_grade

    # FIXED: unified the parameter name to 'state_code'
    def process_user_message(self, user_message, state_code, class_year):
        print(f"\n--- GATEKEEPER AGENT ---")
        print(f"Analyzing message: '{user_message}'")
        
        malicious_keywords = ["ignore previous", "delete database", "change my score", "bypass"]
        if any(keyword in user_message.lower() for keyword in malicious_keywords):
            return "🛡️ Gatekeeper Blocked: Security violation detected."
            
        print("Gatekeeper Approval: Request is safe. Routing to Strategist Agent...")
        return self.strategist_agent_response(user_message, state_code, class_year)

    def strategist_agent_response(self, user_message, state_code, class_year):
        print(f"\n--- STRATEGIST AGENT ---")
        
        # DYNAMIC: Calculate the grade instead of hardcoding
        grade = self.calculate_current_grade(class_year)
        search_keyword = f"Grade {grade}"
        print(f"System State: Student is determined to be in {search_keyword}")
        
        # 1. Agent calls Tool 1: Lookup Brain
        print(f"Action: Calling Tool -> get_merit_threshold({state_code}, {class_year})")
        threshold_data = self.mcp.get_merit_threshold(state_code, class_year)
        
        # 2. Agent calls Tool 2: Semantic Brain with the DYNAMIC keyword
        print(f"Action: Calling Tool -> search_knowledge_base('{search_keyword}')")
        pacing_data = self.mcp.search_knowledge_base(search_keyword)
        
        print("\n--- FINAL AI RESPONSE TO USER ---")
        final_response = (
            f"Based on your profile, {threshold_data} "
            f"Since you are currently in {search_keyword}, your targeted pacing profile dictates: {pacing_data}"
        )
        return final_response

if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    
    # Test a Class of 2027 student (Junior / Grade 11)
    print(orchestrator.process_user_message(
        "What's my plan?", 
        state_code="CA", 
        class_year=2027
    ))