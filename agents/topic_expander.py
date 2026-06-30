import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

class TopicExpanderAgent:
    def __init__(self, *args, **kwargs):
        load_dotenv()
        if "GEMINI_API_KEY" in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"].strip()
            
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"DEBUG: Topic Expander Agent client initialization failed: {str(e)}")
            self.client = None

    def expand_topic(self, topic_name, category=None):
        """Generates a neat inline multi-line description for an SAT topic."""
        # Extract name if it contains colon domain prefix
        display_name = topic_name.split(":")[-1].strip() if ":" in topic_name else topic_name
        
        # Define topic_lower upfront so it is always available
        topic_lower = topic_name.lower()
        
        # Detect math vs reading & writing
        if category:
            is_math = (category.lower() == "math")
        else:
            # Fallback keyword matching
            is_math = not any(w in topic_lower for w in ["read", "write", "grammar", "punctuation", "language", "verbal", "ideas", "conventions", "r/w"])

        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Expand on this SAT topic: {topic_name}",
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are a micro-agent. Given an SAT topic name, return a three-line description. "
                            "Do not use separate markdown headers or bullet points. "
                            "Line 1 MUST strictly follow: 'The [topic_name] is [explanation]. It includes: [sub-units].'\n"
                            "Line 2 MUST start with: 'Remember the key formula [formula]' (for math) or 'Remember the key rule [rule]' (for reading/writing).\n"
                            "Line 3 MUST start with: 'Try a sample problem: [sample question]' (for math) or 'Try a sample question: [sample question]' (for reading/writing).\n"
                            "Separate these three lines with double newlines so they render on separate lines."
                        )
                    )
                )
                return response.text
            except Exception as e:
                print(f"DEBUG: Topic Expander live generation failed: {str(e)}")

        # Fallback Mock Generator in multi-line format
        if is_math:
            if "algebra" in topic_lower or "linear" in topic_lower:
                return (
                    f"The **{display_name}** topic is the study of equations representing lines in a coordinate plane. "
                    "It includes: Slope-Intercept Form, Point-Slope Form, and Systems of Linear Equations.\n\n"
                    "Remember the key formula: $y = mx + b$\n\n"
                    "Try a sample problem: If $3x - y = 12$ and $y = \\frac{3}{2}x$, what is the value of $x$?"
                )
            elif "geometry" in topic_lower or "trig" in topic_lower:
                return (
                    f"The **{display_name}** topic explores the geometric relationships between angles and sides of right triangles. "
                    "It includes: Area and Volume calculations, Right Triangles, and Circle Theorems.\n\n"
                    "Remember the key formula: $a^2 + b^2 = c^2\n\n"
                    "Try a sample problem: A right triangle has legs of length 5 and 12. What is the sine of the angle opposite the leg of length 5?"
                )
            else:
                return (
                    f"The **{display_name}** topic is an essential component of the SAT Math prep curriculum. "
                    "It includes: core concepts, standard solving methods, and targeted test strategies.\n\n"
                    "Remember the key formula: General formulations and equations\n\n"
                    "Try a sample problem: Apply standard SAT math concepts to solve practice questions relating to this domain."
                )
        else:
            if "transition" in topic_lower or "structure" in topic_lower:
                return (
                    f"The **{display_name}** topic focuses on transition words and logical connecting words in academic passages. "
                    "It includes: Cause and Effect connections, Contrast transitions, and Elaboration markers.\n\n"
                    "Remember the key rule: Select transition words that exactly match the logical relationship between sentences.\n\n"
                    "Try a sample question: Which transition word (therefore, however, furthermore) best fits a contrasting relationship?"
                )
            else:
                return (
                    f"The **{display_name}** topic focuses on analyzing argument structures, punctuation patterns, and textual evidence. "
                    "It includes: Rhetorical Synthesis, Transitions, and Boundary Punctuation.\n\n"
                    "Remember the key rule: Relative clauses must be joined to main clauses without creating comma splices.\n\n"
                    "Try a sample question: Analyze text evidence to select the correct choice relating to this domain."
                )