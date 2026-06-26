import os
import json
from google import genai
from google.genai import types
from mcp_server import TestPrepMCPServer

class StrategistAgent:
    """
    Headless Analytical Engine.
    Maps the full Khan Academy curriculum across the student's remaining timeline using the new GenAI SDK.
    """
    def __init__(self, student_id, state_code, class_year):
        self.student_id = student_id
        self.state_code = state_code
        self.class_year = class_year
        self.mcp = TestPrepMCPServer()
        
        # 1. Initialize the new SDK client (automatically picks up GEMINI_API_KEY from environment)
        self.client = genai.Client()
        
        # 2. Define actual Python functions for the agent to call automatically
        def fetch_merit_threshold(state_code: str) -> str:
            """Fetches the National Merit threshold for a state."""
            return str(self.mcp.get_merit_threshold(str(state_code)))

        def fetch_academic_timeline(class_year: int) -> dict:
            """Calculates exact weeks remaining until the next testing milestone."""
            return self.mcp.Skill_Fetch_Academic_Timeline(int(class_year))

        def analyze_performance_gaps(student_id: str) -> dict:
            """Analyzes past scores to identify the student's weakest domain."""
            return self.mcp.Skill_Analyze_Performance_Gaps(str(student_id))

        self.tools = [fetch_merit_threshold, fetch_academic_timeline, analyze_performance_gaps]

        # 3. Define System Instructions
        self.system_instruction = f"""You are a headless TestPrep routing engine analyzing Student {self.student_id} (Class of {self.class_year}, State: {self.state_code}).
        
        Step 1: Call fetch_academic_timeline to determine the exact weeks remaining until their next test.
        Step 2: Call analyze_performance_gaps to determine if they need to prioritize Math or Reading/Writing.
        Step 3: Spread the FULL scope of the Khan Academy Digital SAT prep across the calculated weeks remaining. Every week MUST contain both a Math and a Reading/Writing topic.

        Khan Academy Scope Reference:
        - Math Units: Algebra, Advanced Math, Problem-Solving and Data Analysis, Geometry and Trigonometry.
        - R/W Units: Information and Ideas, Craft and Structure, Expression of Ideas, Standard English Conventions.
        
        Base Links to use:
        Math: https://www.khanacademy.org/test-prep/v2-sat-math
        R/W: https://www.khanacademy.org/test-prep/sat-reading-and-writing
        
        You MUST return ONLY a valid JSON object matching this exact schema. DO NOT wrap the output in markdown blocks (```json).
        {{
            "analysis_summary": "A 2-sentence summary of their timeline and strategic focus.",
            "total_weeks": 12,
            "schedule": [
                {{
                    "week": "Week 1",
                    "math_topic": "Algebra - Linear Equations",
                    "math_link": "url",
                    "rw_topic": "Craft and Structure - Words in Context",
                    "rw_link": "url"
                }}
            ]
        }}"""
        
        # 4. Bundle tools and instructions into the new Config object
        self.config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            tools=self.tools,
            temperature=0.2 # Lower temperature enforces stricter JSON structure
        )

    def generate_action_plan(self):
        hardcoded_prompt = "Execute timeline calculation. Spread the Khan Academy curriculum across the remaining weeks and generate the JSON schedule."
        try:
            # The new SDK's chats.create handles multi-turn automatic function calling seamlessly
            chat = self.client.chats.create(
                model="gemini-2.5-flash", 
                config=self.config
            )
            response = chat.send_message(hardcoded_prompt)
            
            # Clean up the response in case the model added markdown formatting
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            return json.loads(raw_text.strip())
        except Exception as e:
            return {"error": f"Agent failed to generate plan: {str(e)}"}