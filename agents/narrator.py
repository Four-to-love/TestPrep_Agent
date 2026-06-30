import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

class NarratorAgent:
    def __init__(self, *args, **kwargs):
        load_dotenv()
        if "GEMINI_API_KEY" in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"].strip()
            
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"DEBUG: Narrator Agent client initialization failed: {str(e)}")
            self.client = None

    def generate_schedule_summary(self, state_code, target_test_date, pacing_strategy):
        """Generates schedule-specific brief (no emojis, no bold stars, no dates)."""
        if self.client:
            try:
                prompt = f"""
                You are an encouraging and inspiring academic coach writing a personal summary for a high school student aiming to qualify for the National Merit Scholarship through the PSAT/SAT.

                STUDENT PROFILE:
                - State: {state_code}
                
                SCHEDULE DETAILS:
                - Pacing Strategy: {pacing_strategy}
                
                CRITICAL INSTRUCTIONS:
                - Keep the summary brief and highly readable (1 short paragraph).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Do not mention or repeat the student's graduation year.
                - Do not mention any specific test date or year. Instead, state that the schedule will prepare them "by your test".
                - Advise the student to download the schedule to their calendar using the download button to set study reminders.
                - Explain that they can input their future test date to automatically adjust the schedule, ensuring all material is covered on time.
                - Express strong belief in their ability to study hard and qualify for the National Merit Scholarship in {state_code}.
                - Format the output in plain text.
                """
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                print(f"DEBUG: Narrator Agent generate_schedule_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        test_date_phrase = f"before your target test date of {target_test_date}" if target_test_date else "by your test"
        return f"Based on your profile and scores, we have custom-built a study schedule to help you qualify for the prestigious National Merit Scholarship in {state_code}. We have aligned your timeline under the {pacing_strategy.split('.')[0]} pacing strategy. This gives you the optimal balance of concept building and practice testing {test_date_phrase}. To get the most out of your prep, click the Download Calendar button below to add this schedule to your personal calendar for weekly reminders. If you want to adjust your plan, simply enter your target test date in the input field—your timeline will automatically recalculate to make sure everything is covered right on time."

    def generate_math_summary(self):
        """Generates math-specific checklist brief (no emojis, no bold stars)."""
        if self.client:
            try:
                prompt = """
                You are an encouraging academic coach writing a short instruction for a student.
                
                CRITICAL INSTRUCTIONS:
                - Write exactly 1 short paragraph (2-3 sentences).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Explain to the student: do you believe you already know some of these concepts to the point you don't need to practice anymore? Then you can look through the plan for math concepts, practice solving problems, and make sure you remember all the key formulas.
                - Explain that clicking the "Update my Schedule" button will exclude these topics from their timeline (and they can uncheck them to bring them back).
                - Format the output in plain text.
                """
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                print(f"DEBUG: Narrator Agent generate_math_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        return "Do you believe you already know some of these concepts to the point you do not need to practice anymore? Look through the plan for math concepts, practice solving problems, and make sure you remember all the key formulas. If you feel confident, check off what you know. Clicking the Update my Schedule button will exclude these topics from your weekly study tasks so you can focus strictly on new material (and you can always uncheck them to bring them back)."

    def generate_rw_summary(self):
        """Generates R/W-specific checklist brief (no emojis, no bold stars)."""
        if self.client:
            try:
                prompt = """
                You are an encouraging academic coach writing a short instruction for a student.
                
                CRITICAL INSTRUCTIONS:
                - Write exactly 1 short paragraph (2-3 sentences).
                - Do not address the student as "future scholar" or other titles.
                - Remove all emojis, icons, and picture representations.
                - Do not use any bold formatting (remove all double asterisks **).
                - Explain to the student: are there language skills listed here that you have already mastered? Review the plan for reading comprehension, grammar rules, and evidence-based writing, and check what you know.
                - Explain that clicking the "Update my Schedule" button will exclude these topics from their timeline (and they can uncheck them to bring them back).
                - Format the output in plain text.
                """
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                print(f"DEBUG: Narrator Agent generate_rw_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        return "Are there language skills listed here that you have already mastered? Review the plan for reading comprehension, grammar, and evidence-based writing, and check what you know. Clicking the Update my Schedule button will exclude these topics from your weekly study tasks so you can focus strictly on new material (and you can always uncheck them to bring them back)."

    def generate_tutor_summary(self):
        """Generates tutor chat brief (no emojis, no bold stars)."""
        if self.client:
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
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return response.text.strip().replace("**", "").replace("*", "")
            except Exception as e:
                print(f"DEBUG: Narrator Agent generate_tutor_summary failed: {str(e)}")

        # Fallback Mock Generator adhering strictly to user guidelines
        return "Not sure how the PSAT or SAT works? In this chat, you can ask any question about the SAT or PSAT exam, rules, curriculum, and scoring. The tutor will answer your questions strictly using information from official College Board documents."
