# agents/tutor.py
import os
from google import genai
from dotenv import load_dotenv

# 1. Load environment variables from the .env file before initializing
load_dotenv()

class SyllabusTutorAgent:
    def __init__(self, kb_path):
        # 1. Read the file path provided by app.py
        with open(kb_path, 'r', encoding='utf-8') as file:
            self.syllabus_content = file.read()
            
        # 2. Inject it into the system prompt
        self.system_prompt = f"""
        You are the TestPrep_Agent Tutor. You must strictly follow these rules 
        and base all your advice ONLY on the following knowledge base:
        
        {self.syllabus_content}
        """
        
        # 3. Initialize the AI client

        self.client = genai.Client()

    def answer_question(self, user_question: str) -> str:
        """Answers questions strictly using the loaded Markdown syllabus."""
        prompt = f"""
        You are an expert SAT Tutor. Answer the student's question using ONLY the provided syllabus context below.

        SYLLABUS CONTENT:
        {self.syllabus_content}

        INSTRUCTIONS:
        - If the answer to the question is not explicitly contained in the syllabus, you must say exactly: 
          "I cannot find that information in the official SAT framework."
        - Do not use outside knowledge, search the internet, or make assumptions.
        - Provide clear, academic, and encouraging responses.

        STUDENT QUESTION: {user_question}
        """
        
        # Generate response (No tools = No internet access)
        response = self.client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        
        return response.text