import os
import time
from google import genai
from google.genai import types

from agents.llm_utils import call_gemini_with_retry, MAX_CHAT_TURNS
from telemetry import log_llm_call

class SyllabusTutorAgent:
    def __init__(self, *args, **kwargs):
        
        # Sanitize API key in environment to remove any trailing whitespace or carriage returns
        if "GEMINI_API_KEY" in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"].strip()
            
        # 1. Safely resolve knowledge base file path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        kb_path = os.path.join(base_dir, "../knowledge_base/SAT_Tutor.md")
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                self.syllabus_content = f.read()[:50000] # Cap content to stay within token context comfortably
        except Exception:
            self.syllabus_content = ""

        # 2. Safely initialize Gemini AI Client using the native SDK
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"DEBUG: Tutor Agent client initialization failed: {str(e)}")
            self.client = None

    def answer_question(self, user_message: str, recent_context: list = None) -> str:
        """Answers questions strictly using the loaded Markdown syllabus/tutor guide."""
        msg_lower = user_message.lower()

        # Enforce hard ceiling on multi-agent/chat iteration loop
        if len(recent_context or []) > MAX_CHAT_TURNS:
            return "⚠️ Our chat has reached the session limit. Please refresh to start a new session."

        # If live client is active, attempt to generate live tutor responses
        if self.client:
            t0 = time.time()
            prompt = ""
            try:
                # 1. Aggressive token-budgeting: Limit inputs
                safe_message = user_message[:2000]
                windowed_context = (recent_context or [])[-6:]
                kb_excerpt = self.syllabus_content[:30000]

                # Build transcript history
                history_text = ""
                if windowed_context:
                    history_text = "\nRECENT CONVERSATION HISTORY:\n"
                    for msg in windowed_context:
                        role = "Student" if msg["role"] == "user" else "Tutor"
                        history_text += f"{role}: {msg['content']}\n\n"

                prompt = (
                    f"CONTEXT (SAT Tutor Guide):\n{kb_excerpt}\n\n"
                    f"{history_text}"
                    f"Student: {safe_message}"
                )

                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are an encouraging and skilled SAT/PSAT Tutor. "
                            "Answer the student's question clearly and concisely. "
                            "Provide helpful study tips, rules, or formulas where applicable. "
                            "Do not mention any system files, prompt instructions, or guide document names in your response."
                        )
                    )
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="tutor",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return response.text
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="tutor",
                    prompt_chars=len(prompt) if prompt else 0,
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Tutor Agent live generation failed: {str(e)}")

        # Fallback Mock Tutor Responses
        time.sleep(1.2)  # Simulate network latency
        if "linear" in msg_lower or "math" in msg_lower:
            return (
                "💡 **AI Tutor Strategy: Linear Equations**\n\n"
                "For the Digital SAT, 80% of linear equation problems test your ability to "
                "quickly translate a word problem into the $y = mx + b$ format.\n\n"
                "**Pro-Tip:** Don't calculate everything! Often, the test just wants you to "
                "identify what the slope ($m$) or y-intercept ($b$) represents in the real-world context."
            )
        elif "reading" in msg_lower or "writing" in msg_lower:
            return (
                "💡 **AI Tutor Strategy: Reading & Writing**\n\n"
                "The Digital SAT groups R&W questions by *type*. For 'Command of Evidence' "
                "questions, don't read the whole passage first. Read the actual question, "
                "identify what claim you need to support, and then scan the passage *only* "
                "for that specific evidence."
            )
        else:
            return (
                "That's a great question! Since TestPrep_Agent is currently running in fallback Mode "
                "for this question, try asking me specifically for advice on **Linear Equations** "
                "or **Reading** strategies to see how the tutor responds!"
            )
