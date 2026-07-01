import os
import time
from google import genai
from google.genai import types
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

    def generate_schedule_summary(self, state_code, target_test_date, pacing_strategy, graduation_year=None, days_until_test=None, student_name="Student"):
        """Generates schedule-specific brief (no emojis, no bold stars, no dates)."""
        if not student_name or student_name.strip() == "":
            student_name = "Student"
            
        import math
        # 1. Determine pacing context and exact time phrasing
        pacing_context = ""
        time_phrasing = "ample time to prepare"
        
        if days_until_test is not None:
            weeks_remaining = math.ceil(days_until_test / 7)
            if days_until_test < 30:
                time_phrasing = f"{days_until_test} days remaining until your test"
                pacing_context = f"The test is approaching rapidly. Greet {student_name} and explain that this is a high-intensity, fast-paced sprint focusing heavily on practice testing, hacks, and targeted review since they only have {time_phrasing}."
            elif weeks_remaining <= 35:
                time_phrasing = f"{weeks_remaining} weeks remaining until your test"
                pacing_context = f"The test is approaching soon. Greet {student_name} and explain that this is a focused preparation timeline with {time_phrasing}."
            else:
                time_phrasing = "enough time to prepare for your test"
                pacing_context = f"The test is far in the future. Greet {student_name} and explain that this is a balanced, comfortable timeline to build skills and practice since they have enough time to prepare."
        else:
            time_phrasing = "ample time to prepare"
            if graduation_year:
                if graduation_year >= 2030:
                    pacing_context = f"Since no test date is set and you are in 9th grade, greet {student_name} and explain that this is a long-term strategic Foundations approach to build core skills slowly and comfortably (manageable 2 hours/week) to familiarize yourself with the test over time."
                elif graduation_year == 2029:
                    pacing_context = f"Since no test date is set and you are in 10th grade, greet {student_name} and explain that this is an intermediate-term skills development pacing strategy."
                else:
                    pacing_context = f"Since no test date is set and you are in 11th/12th grade, greet {student_name} and explain that this is a standard preparation schedule to prepare you by your upcoming test."

        if self.client:
            t0 = time.time()
            prompt = ""
            try:
                prompt = f"""
                You are an encouraging and inspiring academic coach writing a personal summary for a high school student aiming to qualify for the National Merit Scholarship through the PSAT/SAT.

                STUDENT PROFILE:
                - Name: {student_name}
                - State: {state_code}
                
                PACING STRATEGY INSTRUCTIONS:
                {pacing_context}
                
                CRITICAL INSTRUCTIONS:
                - Keep the summary brief and highly readable (1 short paragraph).
                - Greet the student naturally using their first name {student_name} (never use the word "Student" or other generic titles).
                - Retell the pacing and timeline ideas naturally in your own words based on the PACING STRATEGY INSTRUCTIONS.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Do not mention or repeat the student's graduation year.
                - Do not mention any specific test date or year.
                - Advise the student to download the schedule to their calendar using the download button to set study reminders.
                - Explain that they can input their future test date to automatically adjust the schedule, ensuring all material is covered on time.
                - Express strong belief in their ability to study hard and qualify for the National Merit Scholarship in {state_code}.
                - Format the output in plain text.
                """
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_schedule",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_schedule",
                    prompt_chars=len(prompt) if prompt else 0,
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Narrator Agent generate_schedule_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        test_date_phrase = f"before your target test date of {target_test_date}" if target_test_date else "by your test"
        return f"Based on your profile and scores, we have custom-built a study schedule to help you qualify for the prestigious National Merit Scholarship in {state_code}. We have aligned your timeline under the {pacing_strategy.split('.')[0]} pacing strategy. This gives you the optimal balance of concept building and practice testing {test_date_phrase}. To get the most out of your prep, click the Download Calendar button below to add this schedule to your personal calendar for weekly reminders. If you want to adjust your plan, simply enter your target test date in the input field—your timeline will automatically recalculate to make sure everything is covered right on time."

    def generate_math_summary(self):
        """Generates math-specific checklist brief (no emojis, no bold stars)."""
        if self.client:
            t0 = time.time()
            prompt = ""
            try:
                prompt = """
                You are an encouraging academic coach writing a short orientation note for a student.

                CRITICAL INSTRUCTIONS:
                - Write exactly 1 short paragraph (3-4 sentences).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Tell the student: look through the Math concept list below. Every topic or skill they already know can be checked off with the checkmark button on the right — once checked, it is automatically removed from their weekly schedule so they can focus only on what is new.
                - Mention that if they want to understand any topic or skill better before deciding, they can click the question mark (?) button next to it for an instant AI explanation.
                - Mention that they can uncheck anything at any time to bring it back into their schedule.
                - Format the output in plain text.
                """
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_math",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_math",
                    prompt_chars=len(prompt) if prompt else 0,
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Narrator Agent generate_math_summary failed: {str(e)}")

        # Fallback
        return (
            "Look through the Math concept list below and check off anything you have already mastered. "
            "Once checked, that topic is automatically removed from your weekly schedule so you can focus on what is new. "
            "Not sure whether you know a topic well enough? Click the question mark (?) button next to it for an instant AI explanation. "
            "You can uncheck any topic at any time to bring it back into your plan."
        )

    def generate_rw_summary(self):
        """Generates R/W-specific checklist brief (no emojis, no bold stars)."""
        if self.client:
            t0 = time.time()
            prompt = ""
            try:
                prompt = """
                You are an encouraging academic coach writing a short orientation note for a student.

                CRITICAL INSTRUCTIONS:
                - Write exactly 1 short paragraph (3-4 sentences).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Tell the student: look through the Reading and Writing skill list below. Every skill they have already mastered can be checked off with the checkmark button on the right — once checked, it is automatically removed from their weekly schedule so they can focus only on what is new.
                - Mention that if they want to understand any skill better before deciding, they can click the question mark (?) button next to it for an instant AI explanation.
                - Mention that they can uncheck anything at any time to bring it back into their schedule.
                - Format the output in plain text.
                """
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_rw",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_rw",
                    prompt_chars=len(prompt) if prompt else 0,
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Narrator Agent generate_rw_summary failed: {str(e)}")

        # Fallback
        return (
            "Look through the Reading and Writing skill list below and check off anything you have already mastered. "
            "Once checked, that skill is automatically removed from your weekly schedule so your prep time goes toward what is still new. "
            "Not sure whether you have truly nailed a skill? Click the question mark (?) button next to it for an instant AI explanation. "
            "You can uncheck any skill at any time to bring it back into your plan."
        )

    def generate_tutor_summary(self):
        """Generates tutor chat brief (no emojis, no bold stars)."""
        if self.client:
            t0 = time.time()
            prompt = ""
            try:
                prompt = """
                You are an encouraging academic coach writing a short instruction for a student.
                
                CRITICAL INSTRUCTIONS:
                - Write exactly 1 short paragraph (2-3 sentences).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Explain to the student: in this chat, they can ask any question about the SAT or PSAT exam, rules, curriculum, and scoring.
                - Explain that the tutor will answer their questions strictly using information from official College Board documents.
                - Format the output in plain text.
                """
                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_tutor",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="narrator_tutor",
                    prompt_chars=len(prompt) if prompt else 0,
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Narrator Agent generate_tutor_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        return "Not sure how the PSAT or SAT works? In this chat, you can ask any question about the SAT or PSAT exam, rules, curriculum, and scoring. The tutor will answer your questions strictly using information from official College Board documents."
