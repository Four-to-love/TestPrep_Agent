import os
import time
from google import genai
from agents.llm_utils import call_gemini_with_retry
from telemetry import log_llm_call

class NarratorAgent:
    def __init__(self, *args, **kwargs):
        if "GEMINI_API_KEY" in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"].strip()

        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"DEBUG: Narrator Agent client initialization failed: {str(e)}")
            self.client = None

    def generate_schedule_summary(
        self,
        state_code,
        target_test_date,
        pacing_strategy,
        graduation_year=None,
        days_until_test=None,
        student_name="Student",
        mastered_count=0,
        total_skills=0,
    ):
        """Generates a warm, personal schedule paragraph referencing mastered skill count and time left."""
        if not student_name or student_name.strip() == "":
            student_name = "Student"

        import math as _math
        weeks_remaining = _math.ceil(days_until_test / 7) if days_until_test and days_until_test > 0 else None

        if days_until_test is not None and days_until_test < 30:
            time_fact = f"{days_until_test} days until the test"
        elif weeks_remaining is not None:
            time_fact = f"{weeks_remaining} weeks until the test"
        else:
            time_fact = "plenty of time to prepare before the test"

        progress_fact = (
            f"{mastered_count} out of {total_skills} skills already mastered"
            if total_skills > 0 and mastered_count > 0
            else "just getting started - no skills checked off yet"
        )

        prompt = f"""You are a warm, encouraging academic coach writing a personal, engaging note for a high school student preparing for the SAT/PSAT and aiming to qualify for the National Merit Scholarship in {state_code}.

Student name: {student_name}
Time left: {time_fact}
Progress: {progress_fact}
Current pacing strategy: {pacing_strategy}

Write 5-7 sentences directly to {student_name}. Use their name naturally. Weave in the time and progress facts conversationally. Be warm, vivid, and encouraging. Express genuine belief in their ability to qualify for National Merit in {state_code}. Mention they can enter their target test date to auto-adjust the schedule, and download it to their calendar. You may use bold text, bullet points, and a few relevant emojis to make the message feel lively and motivating.
"""

        if self.client:
            t0 = time.time()
            try:
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_schedule",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok",
                )
                return response.text.strip()
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_schedule",
                    prompt_chars=len(prompt),
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error",
                )
                print(f"DEBUG: Narrator generate_schedule_summary failed: {str(e)}")

        return (
            f"You have a personalized study plan built just for you, {student_name}. "
            f"With {progress_fact} and {time_fact}, your schedule is optimized to cover everything on time. "
            f"Enter your target test date to auto-adjust the timeline, and download it to your calendar to stay on track. "
            f"You have what it takes to qualify for the National Merit Scholarship in {state_code}."
        )

    def generate_math_summary(
        self,
        student_name="Student",
        last_mastered_math=None,
        next_math=None,
    ):
        """Generates a personal Math tab paragraph referencing the student's last mastered and next Math skill."""
        if not student_name or student_name.strip() == "":
            student_name = "Student"

        if last_mastered_math and next_math:
            progress_context = (
                f'The last Math skill they mastered is: "{last_mastered_math}". '
                f'The next Math skill they have not studied yet is: "{next_math}".'
            )
        elif last_mastered_math and not next_math:
            progress_context = (
                f'They have mastered every Math skill on the list, most recently "{last_mastered_math}". '
                "Encourage them to focus on full-length practice tests."
            )
        else:
            progress_context = (
                "They have not checked off any Math skills yet. "
                f"Encourage {student_name} to look through the list and check off anything they already know - "
                "every checked skill is automatically removed from their weekly schedule."
            )

        prompt = f"""You are a warm, encouraging academic coach writing a personal, engaging note for {student_name} about their Math prep.

Context: {progress_context}

Write 5-7 sentences directly to {student_name}. Use their name naturally once. Acknowledge their Math progress warmly and specifically — call out what they accomplished. If they have a next skill, name it and encourage them to tackle it next; mention the question mark (?) button for an instant AI explanation before they dive in. Remind them that checking off a skill removes it from their schedule so they only study what is new. You may use bold text, bullet points, and a few relevant emojis to make the message feel lively and motivating.
"""

        if self.client:
            t0 = time.time()
            try:
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_math",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok",
                )
                return response.text.strip()
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_math",
                    prompt_chars=len(prompt),
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error",
                )
                print(f"DEBUG: Narrator generate_math_summary failed: {str(e)}")

        if next_math:
            return (
                f"Great work so far, {student_name}. Your next Math topic to tackle is {next_math}. "
                "Click the question mark button next to any skill for an instant AI explanation, "
                "and check off anything you already know to keep your schedule focused on what is new."
            )
        return (
            f"Look through the Math list below, {student_name}, and check off anything you have already mastered. "
            "Once checked, that skill is removed from your weekly schedule automatically. "
            "Use the question mark button for an instant AI explanation of any topic you want to review first."
        )

    def generate_rw_summary(
        self,
        student_name="Student",
        last_mastered_rw=None,
        next_rw=None,
    ):
        """Generates a personal Reading & Writing tab paragraph referencing the student's last mastered and next RW skill."""
        if not student_name or student_name.strip() == "":
            student_name = "Student"

        if last_mastered_rw and next_rw:
            progress_context = (
                f'The last Reading & Writing skill they mastered is: "{last_mastered_rw}". '
                f'The next Reading & Writing skill they have not studied yet is: "{next_rw}".'
            )
        elif last_mastered_rw and not next_rw:
            progress_context = (
                f'They have mastered every Reading & Writing skill, most recently "{last_mastered_rw}". '
                "Encourage them to focus on full-length practice tests."
            )
        else:
            progress_context = (
                "They have not checked off any Reading & Writing skills yet. "
                f"Encourage {student_name} to go through the list and check off anything they already know - "
                "every checked skill is automatically removed from their weekly schedule."
            )

        prompt = f"""You are a warm, encouraging academic coach writing a personal, engaging note for {student_name} about their Reading and Writing prep.

Context: {progress_context}

Write 5-7 sentences directly to {student_name}. Use their name naturally once. Acknowledge their Reading & Writing progress warmly and specifically — call out what they accomplished. If they have a next skill, name it and encourage them to tackle it; mention the question mark (?) button for an instant AI explanation. Remind them that checking off a skill removes it from their schedule so they only study what is new. You may use bold text, bullet points, and a few relevant emojis to make the message feel lively and motivating.
"""

        if self.client:
            t0 = time.time()
            try:
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_rw",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok",
                )
                return response.text.strip()
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_rw",
                    prompt_chars=len(prompt),
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error",
                )
                print(f"DEBUG: Narrator generate_rw_summary failed: {str(e)}")

        if next_rw:
            return (
                f"Nice progress, {student_name}. Your next Reading & Writing skill to study is {next_rw}. "
                "Click the question mark next to any skill for an instant explanation, "
                "and check off what you know to keep your plan tight."
            )
        return (
            f"Look through the Reading & Writing list below, {student_name}, and check off anything you have already mastered. "
            "Once checked, that skill is removed from your weekly schedule automatically. "
            "Use the question mark button for an instant AI explanation of any skill you want to review first."
        )

    def generate_tutor_summary(
        self,
        student_name="Student",
        days_until_test=None,
    ):
        """Generates a time-aware tutor intro with a warm encouragement and a practical study tip."""
        if not student_name or student_name.strip() == "":
            student_name = "Student"

        import math as _math
        if days_until_test is not None and days_until_test > 0:
            weeks_remaining = _math.ceil(days_until_test / 7)
            if days_until_test < 14:
                time_context = f"The test is only {days_until_test} days away - this is the final stretch."
            elif weeks_remaining <= 6:
                time_context = f"With {weeks_remaining} weeks to go, the test is coming up soon."
            else:
                time_context = f"There are {weeks_remaining} weeks until the test - enough time to build real confidence."
        else:
            time_context = "The test is on the horizon and every study session counts."

        prompt = f"""You are a warm, encouraging academic coach writing a personal, engaging intro for {student_name} before they use an AI tutor chat.

Context: {time_context}

Write 5-7 sentences directly to {student_name}. Acknowledge the exam timeline warmly. Encourage them to use this chat to ask anything about the SAT or PSAT - rules, topics, scoring, strategy. Mention the tutor answers from official College Board materials. End with one practical, specific study tip (for example: quality sleep the night before a practice test improves recall, or timed practice sections train your pacing instinct). Keep it warm, personal, and energising. You may use bold text, bullet points, and a few relevant emojis to make the message feel lively and motivating.
"""

        if self.client:
            t0 = time.time()
            try:
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_tutor",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok",
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_tutor",
                    prompt_chars=len(prompt),
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error",
                )
                print(f"DEBUG: Narrator generate_tutor_summary failed: {str(e)}")

        return (
            f"You've got this, {student_name}. Use this chat to ask anything about the SAT or PSAT - "
            "exam rules, topics, scoring, or strategy. The tutor answers strictly from official College Board materials. "
            "One tip: getting a full night of sleep before a practice test makes a real difference in how you perform."
        )
