# skills_registry.py

AGENT_SKILLS = [
    {
        "type": "function",
        "function": {
            "name": "Skill_Fetch_Academic_Timeline",
            "description": "Calculates the exact weeks remaining until the PSAT or SAT based on the student's graduation year and the current date, returning a structured timeline and urgency level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "class_year": {
                        "type": "integer",
                        "description": "The student's expected graduation year (e.g., 2026, 2027)."
                    }
                },
                "required": ["class_year"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Skill_Query_National_Merit_Threshold",
            "description": "Queries the exact National Merit Selection Index cutoff for a specific state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state_code": {
                        "type": "string",
                        "description": "The 2-letter US state abbreviation."
                    },
                    "class_year": {
                        "type": "integer",
                        "description": "The student's graduation year."
                    }
                },
                "required": ["state_code", "class_year"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "Skill_Analyze_Performance_Gaps",
            "description": "Pulls historical practice scores to identify the weakest domains (Math vs Reading/Writing) and calculate score trajectories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "The unique identifier for the student."
                    }
                },
                "required": ["student_id"]
            }
        }
    }
]