import time

# =====================================================================
# DEMO MODE: ACTIVE LIVE AGENT MOCK
# =====================================================================
class TopicExpanderAgent:
    def __init__(self, *args, **kwargs):
        pass

    def expand_topic(self, topic_name):
        """Simulates the micro-agent generating sub-units and formulas."""
        time.sleep(1.0)
        topic_lower = topic_name.lower()
        
        if "algebra" in topic_lower or "linear" in topic_lower:
            return (
                "### Sub-Units\n"
                "* Linear Equations & Inequalities\n"
                "* Systems of Linear Equations\n"
                "* Graphing Linear Functions\n\n"
                "### Key Formulas\n"
                "* **Slope-Intercept Form:** $y = mx + b$\n"
                "* **Point-Slope Form:** $y - y_1 = m(x - x_1)$\n\n"
                "### Sample Question\n"
                "If $3x - y = 12$ and $y = \\frac{3}{2}x$, what is the value of $x$?"
            )
        elif "geometry" in topic_lower or "trig" in topic_lower:
            return (
                "### Sub-Units\n"
                "* Area and Volume\n"
                "* Right Triangles and Trigonometry\n"
                "* Circle Theorems\n\n"
                "### Key Formulas\n"
                "* **Pythagorean Theorem:** $a^2 + b^2 = c^2$\n"
                "* **Area of a Circle:** $A = \\pi r^2$\n\n"
                "### Sample Question\n"
                "A right triangle has legs of length 5 and 12. What is the sine of the angle opposite the leg of length 5?"
            )
        else:
            return (
                f"### Topic: {topic_name}\n"
                "*Demo Mode: Sub-units, formulas, and sample questions for this specific module will populate when the live API is restored.*"
            )

# =====================================================================
# PRODUCTION CODE (PROD IMPLEMENTATION - INACTIVE via comment hashes)
# =====================================================================
# import os
# from dotenv import load_dotenv
# from google import genai
# 
# class ProductionTopicExpanderAgent:
#     def __init__(self, *args, **kwargs):
#         load_dotenv()
#         api_key = os.getenv("GEMINI_API_KEY")
#         if api_key:
#             api_key = api_key.strip()
#         self.client = genai.Client(api_key=api_key)
# 
#     def expand_topic(self, topic_name):
#         try:
#             response = self.client.models.generate_content(
#                 model='gemini-1.5-flash',
#                 contents=f"Expand on this SAT topic: {topic_name}",
#                 config={
#                     'system_instruction': (
#                         "You are a micro-agent. Given an SAT topic, return exactly three sections "
#                         "formatted in Markdown: ### Sub-Units (bulleted list), ### Key Formulas "
#                         "(use LaTeX formatting), and ### Sample Question. Do not include introductory text."
#                     )
#                 }
#             )
#             return response.text
#         except Exception as e:
#             return f"Production API Error: {str(e)}"