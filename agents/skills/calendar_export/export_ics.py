import os
import datetime
from ics import Calendar, Event

def export_schedule_to_ics(schedule_df) -> str:
    """Generate an .ics file from the schedule DataFrame.

    The DataFrame is expected to have a column ``Week`` whose value looks like
    ``"Week 1\nJanuary, 01"``. The function extracts the week number, computes a
    start date (today + (week-1) weeks) and uses the ``Math Focus`` and ``Reading & Writing Focus``
    columns as the event description.

    Returns the absolute path to the generated .ics file.
    """
    # Ensure output directory exists inside the project
    output_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(output_dir, exist_ok=True)
    ics_path = os.path.join(output_dir, "schedule.ics")

    cal = Calendar()
    today = datetime.date.today()

    for _, row in schedule_df.iterrows():
        # Parse week number from the "Week" column (e.g., "Week 3\nMarch, 15")
        week_str = str(row.get("Week", ""))
        # Split on whitespace and take the number after "Week"
        try:
            week_num = int(week_str.split()[1])
        except Exception:
            week_num = 1
        start_date = today + datetime.timedelta(weeks=week_num - 1)

        # Build description using the two focus columns
        math_focus = str(row.get("Math Focus", "")).replace("\n", ", ")
        rw_focus = str(row.get("Reading & Writing Focus", "")).replace("\n", ", ")
        description = f"Math: {math_focus}\nReading & Writing: {rw_focus}"

        event = Event()
        event.name = f"Study Week {week_num}"
        event.begin = start_date.isoformat()
        event.duration = {"days": 7}
        event.description = description
        cal.events.add(event)

    # Write the calendar to file
    with open(ics_path, "w", encoding="utf-8") as f:
        f.writelines(cal)

    return ics_path
