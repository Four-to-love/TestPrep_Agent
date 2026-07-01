import os
import uuid
import datetime

def fold_line(text: str) -> list:
    """
    Safely folds text to 75 octets per RFC 5545 without breaking multi-byte UTF-8 characters.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= 75:
        return [text]

    parts = []
    while len(encoded) > 0:
        max_bytes = 75 if not parts else 74

        if len(encoded) <= max_bytes:
            chunk = encoded
            encoded = b""
        else:
            # Step backward to find a safe UTF-8 character boundary
            cut_index = max_bytes
            while cut_index > 0 and (encoded[cut_index] & 0xC0) == 0x80:
                cut_index -= 1
            
            chunk = encoded[:cut_index]
            encoded = encoded[cut_index:]

        prefix = b" " if parts else b""
        parts.append((prefix + chunk).decode("utf-8"))

    return parts

def export_schedule_to_ics(schedule_df) -> str:
    """Generate a sanitized .ics file from the schedule DataFrame."""
    output_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(output_dir, exist_ok=True)
    ics_path = os.path.join(output_dir, "schedule.ics")

    current_year = datetime.date.today().year

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TestPrep Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for _, row in schedule_df.iterrows():
        week_str = str(row.get("Week", ""))
        try:
            date_part = week_str.split("\n")[1].strip()
            week_start_date = datetime.datetime.strptime(
                f"{date_part} {current_year}", "%B, %d %Y"
            ).date()
        except Exception:
            try:
                week_num = int(week_str.split()[1])
            except Exception:
                week_num = 1
            week_start_date = datetime.date.today() + datetime.timedelta(weeks=week_num - 1)

        start_dt = datetime.datetime(
            week_start_date.year, week_start_date.month, week_start_date.day,
            16, 30
        )
        end_dt = start_dt + datetime.timedelta(hours=2)

        dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
        dtend   = end_dt.strftime("%Y%m%dT%H%M%S")

        # DEFENSIVE ENGINEERING: Sanitize raw newlines into literal '\n' strings
        math_focus = str(row.get("Math Focus", "")).replace("\r", "").replace("\n", "\\n")
        rw_focus   = str(row.get("Reading & Writing Focus", "")).replace("\r", "").replace("\n", "\\n")
        
        description = (
            f"Math:\\n{math_focus}\\n\\nReading & Writing:\\n{rw_focus}"
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}@testprepagent",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
        ]
        lines += fold_line("SUMMARY:SAT Prep time. Check the tasks by opening the event.")
        lines += fold_line(f"DESCRIPTION:{description}")
        lines += ["END:VEVENT"]

    lines.append("END:VCALENDAR")

    with open(ics_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")

    return ics_path