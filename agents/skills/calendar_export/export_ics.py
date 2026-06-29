import os
import uuid
import datetime

def export_schedule_to_ics(schedule_df) -> str:
    """Generate an .ics file from the schedule DataFrame.

    The DataFrame is expected to have a column ``Week`` whose value looks like
    ``"Week 1\\nJune, 30"``. The function parses the date from that string and
    schedules one event per week at 4:30 PM **in the student's local timezone**,
    lasting 2 hours.

    The ICS file uses floating time (no UTC offset, no TZID) so every calendar
    app — Google Calendar, Apple Calendar, Outlook — will display the event at
    4:30 PM in whatever timezone the student's device is set to.

    Returns the absolute path to the generated .ics file.
    """
    # Ensure output directory exists inside the project
    output_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(output_dir, exist_ok=True)
    ics_path = os.path.join(output_dir, "schedule.ics")

    current_year = datetime.date.today().year

    # ICS boilerplate — written manually so we control the time format exactly
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SAT Prep Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for _, row in schedule_df.iterrows():
        # Parse the date from the "Week" column (e.g., "Week 1\nJune, 30")
        week_str = str(row.get("Week", ""))
        try:
            # Second line holds the date, e.g. "June, 30"
            date_part = week_str.split("\n")[1].strip()
            week_start_date = datetime.datetime.strptime(
                f"{date_part} {current_year}", "%B, %d %Y"
            ).date()
        except Exception:
            # Fallback: derive from week number relative to today
            try:
                week_num = int(week_str.split()[1])
            except Exception:
                week_num = 1
            week_start_date = datetime.date.today() + datetime.timedelta(weeks=week_num - 1)

        # Build floating datetimes — NO 'Z', NO tzinfo → student's local time
        start_dt = datetime.datetime(
            week_start_date.year, week_start_date.month, week_start_date.day,
            16, 30  # 4:30 PM
        )
        end_dt = start_dt + datetime.timedelta(hours=2)  # 6:30 PM

        # ICS format: YYYYMMDDTHHmmSS (no Z = floating / local time)
        dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend   = end_dt.strftime("%Y%m%dT%H%M%S")

        # Build description — escape commas and semicolons per RFC 5545
        math_focus = str(row.get("Math Focus", ""))
        rw_focus   = str(row.get("Reading & Writing Focus", ""))
        description = (
            f"Math:\\n{math_focus}\\n\\nReading & Writing:\\n{rw_focus}"
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@satprepagent",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            "SUMMARY:SAT Prep time. Check the tasks by opening the event.",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")

    # ICS spec requires CRLF line endings
    with open(ics_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")

    return ics_path
