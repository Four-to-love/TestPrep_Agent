# agents/strategist.py

from agents.skills.curriculum_mapper.scheduler_skill import generate_schedule
from agents.skills.test_date_calculator.date_engine import calculate_test_date
from datetime import date

class StrategyEngine:
    def __init__(self):
        pass

    def generate_adaptive_timeline(self, graduation_year: int, test_date_str: str, math_score: int, rw_score: int, mastered_skills: list) -> dict:
        if mastered_skills is None:
            mastered_skills = []
            
        date_info = calculate_test_date(graduation_year, test_date_str)
        weeks_remaining = date_info.get("weeks_remaining", 4)
        
        # --- NEW: Multi-Grade Pacing and Test Frequency Logic ---
        current_year = date.today().year
        years_until_grad = graduation_year - current_year

        if years_until_grad > 2:
            pacing_strategy = "Foundations (9th). Max 2 hours prep/week. Test only to make yourself familiar with the test."
            test_frequency = 15
        elif years_until_grad == 2:
            pacing_strategy = "PSAT/NMSQT Focus (10th). Foundational review with regular testing."
            test_frequency = 6
        elif years_until_grad == 1:
            pacing_strategy = "Primary SAT Year (11th). Aggressive review (3-5 hours/week)."
            test_frequency = 4 # <--- Here is your 4-week rule!
        else:
            pacing_strategy = "Acceleration Protocol. Focus purely on weak areas in each Unit."
            test_frequency = 2

        # 2. Pass the new 'test_frequency' to the Math mapper
        math_plan = generate_schedule(
            weeks_remaining=weeks_remaining,
            strategy=pacing_strategy,
            test_frequency=test_frequency,
            syllabus_file="math_granular_syllabus.json", 
            mastered_skills=mastered_skills
        )
        
        # 3. Pass the new 'test_frequency' to the RW mapper
        rw_plan = generate_schedule(
            weeks_remaining=weeks_remaining,
            strategy=pacing_strategy,
            test_frequency=test_frequency,
            syllabus_file="rw_granular_syllabus.json",
            mastered_skills=mastered_skills
        )

        if "error" in math_plan:
            return {"error": f"Math Scheduler Error: {math_plan['error']}"}
        if "error" in rw_plan:
            return {"error": f"RW Scheduler Error: {rw_plan['error']}"}

        if math_score < rw_score:
            focus = "Math Prioritization - Dedicate 70% of weekly study time to the Math tasks."
        elif rw_score < math_score:
            focus = "Reading & Writing Prioritization - Dedicate 70% of weekly study time to the RW tasks."
        else:
            focus = "Balanced Review - Split weekly study time 50/50 between Math and RW tasks."

        return {
            "overall_focus": focus,
            "target_test_date": date_info.get("test_date"),
            "weeks_remaining": weeks_remaining, 
            "pacing_strategy": pacing_strategy, 
            "schedules": {
                "math": math_plan.get("timeline"),
                "reading_writing": rw_plan.get("timeline")
            }
        }