# skills/curriculum_mapper/scheduler_skill.py
import json
import math
import os

# Added test_frequency argument
def generate_schedule(weeks_remaining: int, strategy: str, test_frequency: int, syllabus_file: str, mastered_skills: list = None) -> dict:
    if mastered_skills is None:
        mastered_skills = []

    try:
        file_path = os.path.join(os.path.dirname(__file__), syllabus_file)
        with open(file_path, 'r') as f:
            syllabus = json.load(f)
    except FileNotFoundError:
        return {"error": f"Could not find {syllabus_file} in the skill directory."}

    study_items = []
    for unit in syllabus.get("units", []):
        domain = unit.get("domain")
        for topic in unit.get("topics", []):
            topic_name = topic.get("name")
            for skill in topic.get("granular_skills", []):
                full_name = f"{domain}: {topic_name} - {skill}"
                if full_name not in mastered_skills:
                    study_items.append(full_name)
    
    total_items = len(study_items)
    
    if total_items == 0:
        return {
            "section": syllabus.get("section", "Test Prep"),
            "weeks_remaining": weeks_remaining,
            "strategy": "All syllabus skills mastered! Focus strictly on full-length practice exams.",
            "timeline": []
        }

    items_per_week = math.ceil(total_items / weeks_remaining)
    
    timeline = []
    item_index = 0
    
    for week in range(1, weeks_remaining + 1):
        week_focus = study_items[item_index:item_index + items_per_week]
        
        # --- NEW: Inject Practice Test into the timeline ---
        if test_frequency > 0 and week % test_frequency == 0:
            week_focus.append("🎯 FULL-LENGTH DIGITAL PRACTICE TEST")

        if week_focus:
            timeline.append({
                "week": week,
                "tasks": week_focus
            })
        item_index += items_per_week

    return {
        "section": syllabus.get("section", "Test Prep"),
        "weeks_remaining": weeks_remaining,
        "items_per_week": items_per_week,
        "strategy": strategy,
        "timeline": timeline
    }