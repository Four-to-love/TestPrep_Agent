# .agents/skills/target-date-calculator/date_engine.py
from datetime import date, datetime

def calculate_test_date(graduation_year: int, explicit_date_str: str = None) -> dict:
    """
    Determines the test_date based on explicit user input or 
    defaults to the Junior year National Merit PSAT date.
    """
    today = date.today()
    
    if explicit_date_str:
        try:
            test_date = datetime.strptime(explicit_date_str, "%Y-%m-%d").date()
            source = "User-Provided Exact Date"
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
    else:
        # Junior year happens the calendar year before they graduate
        psat_year = graduation_year - 1
        test_date = date(psat_year, 9, 15)
        source = "Calculated National Merit PSAT Target (Sept 15 of 11th Grade)"
        
    weeks_remaining = max(1, (test_date - today).days // 7)
    
    return {
        "test_date": test_date.strftime("%Y-%m-%d"),
        "weeks_remaining": weeks_remaining,
        "source": source
    }