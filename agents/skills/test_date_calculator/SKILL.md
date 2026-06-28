# Description
Use this skill whenever you need to determine a student's test date for the PSAT or SAT, or calculate how many weeks they have remaining to study.

# Goal
Provide an exact test date (YYYY-MM-DD) and a countdown in weeks.

# Instructions
1. You must know the student's `graduation_year` to use this skill. If you do not have it from their profile or conversation, ask for it.
2. Check if the user has provided an explicit test date (the `explicit_date_str`).
3. Run the `calculate_test_date` function in `date_engine.py` using `graduation_year` and (if available) `explicit_date_str`.
4. Return the calculated `test_date` and `weeks_remaining`.

# Constraints
- If the user does not provide an exact test date, do NOT ask for one. Simply pass `None` to the script so it can calculate the default Junior year National Merit PSAT date.
- Always communicate the `source` of the date to the user (e.g., "Since you don't have a date yet, I'm mapping this to the National Merit PSAT on September 15th of your Junior year.").