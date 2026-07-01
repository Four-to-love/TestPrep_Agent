import os
import time
from google import genai
from google.genai import types
from agents.llm_utils import call_gemini_with_retry
from telemetry import log_llm_call

class TopicExpanderAgent:
    def __init__(self, *args, **kwargs):
        if "GEMINI_API_KEY" in os.environ:
            os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"].strip()

        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"DEBUG: Topic Expander Agent client initialization failed: {str(e)}")
            self.client = None

    def expand_topic(self, topic_name, category=None, graduation_year=2028, target_test_date=""):
        import datetime
        import math
        import json
        from mcp_client import call_mcp_tool
        
        # Calculate days_until_test
        days_until_test = 90
        if target_test_date:
            try:
                test_date = datetime.datetime.strptime(target_test_date, "%Y-%m-%d").date()
                days_until_test = (test_date - datetime.date.today()).days
                if days_until_test < 0:
                    days_until_test = 0
            except Exception:
                pass
                
        # Calculate weeks_remaining
        weeks_remaining = math.ceil(days_until_test / 7)
        if weeks_remaining <= 0:
            weeks_remaining = 1
            
        # 1. Fetch from Cache via MCP tool
        try:
            cache_resp_str = call_mcp_tool("get_cached_topic_expansion", {
                "topic_name": topic_name,
                "graduation_year": int(graduation_year),
                "weeks_remaining": int(weeks_remaining)
            })
            cache_resp = json.loads(cache_resp_str)
            if cache_resp.get("status") == "found":
                return cache_resp.get("data")
        except Exception as e:
            print(f"DEBUG: MCP Cache check failed: {str(e)}")

        # 2. Cache miss -> Run generator
        res = self._expand_topic_uncached(topic_name, category, graduation_year, days_until_test)
        
        # 3. Save to Cache via MCP tool
        if res:
            try:
                call_mcp_tool("save_topic_expansion", {
                    "topic_name": topic_name,
                    "graduation_year": int(graduation_year),
                    "weeks_remaining": int(weeks_remaining),
                    "expansion_markdown": res
                })
            except Exception as e:
                print(f"DEBUG: MCP Cache save failed: {str(e)}")
                
        return res

    def _expand_topic_uncached(self, topic_name, category=None, graduation_year=2028, days_until_test=90):
        """Generates a rich inline card for an SAT topic."""
        display_name = topic_name.split(":")[-1].strip() if ":" in topic_name else topic_name
        topic_lower = topic_name.lower()

        # Detect math vs reading & writing
        if category:
            is_math = (category.lower() == "math")
        else:
            is_math = not any(w in topic_lower for w in [
                "read", "write", "grammar", "punctuation", "language",
                "verbal", "ideas", "conventions", "r/w"
            ])

        # Derive Grade Level Complexity
        grade_level = "Junior (Standard SAT Complexity)"
        complexity_instruction = "Use standard SAT complexity, providing clear step-by-step math reasoning and standard vocabulary."
        if graduation_year >= 2030:
            grade_level = "Middle Schooler / Freshman"
            complexity_instruction = "Use lower complexity, explaining fundamental math concepts simply and using beginner-friendly grammar terms."
        elif graduation_year == 2029:
            grade_level = "Sophomore"
            complexity_instruction = "Use medium complexity, reinforcing foundational algebra rules and basic sentence structure elements."
        elif graduation_year <= 2027:
            grade_level = "Senior"
            complexity_instruction = "Use high complexity, skipping trivial steps in proofs, using advanced vocabulary, and focusing on high-scorer nuances."

        # Derive Strategic Focus
        strategic_focus = "Balanced (Theory & Strategies)"
        focus_instruction = "Provide a balanced overview of both core theoretical rules and common test-taking strategies."
        if days_until_test > 90:
            strategic_focus = "Deep Concept Mastery / Theory"
            focus_instruction = "Focus heavily on deep theoretical understanding, proofs, grammatical concepts, and fundamental mastery. Avoid shortcuts."
        elif days_until_test < 30:
            strategic_focus = "High-Speed Test Hacks & Shortcuts"
            focus_instruction = "Focus heavily on test-hacks, guessing strategies, structural elimination, time-saving tricks, and shortcut formulas."

        student_context = (
            f"\n\nStudent Context:\n"
            f"- Grade Level: {grade_level} (Graduation Year: {graduation_year})\n"
            f"- Time Context: {days_until_test} days remaining until test.\n"
            f"- Complexity Requirement: {complexity_instruction}\n"
            f"- Strategic Focus: {focus_instruction}"
        )

        if self.client:
            t0 = time.time()
            prompt = f"Generate an SAT study card for the topic: {topic_name}"
            try:
                if is_math:
                    system_instruction = (
                        "You are a concise SAT Math tutor. Given an SAT Math topic name, return a structured card with exactly these sections:\n\n"
                        "**Overview**: One short paragraph (2-3 sentences) explaining what this topic is about and why it appears on the SAT.\n\n"
                        "**Key Formulas**: A numbered list of exactly 5 key formulas or mathematical facts for this topic. Use LaTeX inline math notation (e.g. $y = mx + b$).\n\n"
                        "**Sample Problems**: Exactly 2 practice SAT-style problems with brief solutions.\n\n"
                        "CRITICAL: Do NOT start with a title, heading, or topic name. Begin immediately with '**Overview**:'. No H1, H2, or H3 markdown headings anywhere in the output.\n\n"
                        "For systems of equations or linear equation word problems, you MUST output exactly these two sample problems:\n"
                        "Problem 1: A store sells two types of tickets for a concert: general admission and VIP. A general admission ticket costs 30 dollars, and a VIP ticket costs 75 dollars. On a particular night, the store sold a total of 50 tickets and collected 2,400 dollars in revenue. If **g** represents the number of general admission tickets sold and **v** represents the number of VIP tickets sold, which system of equations represents this situation?\n"
                        "A) **g + v = 50**, **30g + 75v = 2400**\n"
                        "B) **g + v = 2400**, **30g + 75v = 50**\n"
                        "C) **75g + 30v = 50**, **g + v = 2400**\n"
                        "D) **g + v = 50**, **75g + 30v = 2400**\n"
                        "Solution: The total number of tickets sold is 50, so **g + v = 50**. The total revenue is 2,400, and since general admission tickets cost 30 dollars and VIP tickets cost 75 dollars, the revenue equation is **30g + 75v = 2400**. Thus, option A is correct.\n\n"
                        "Problem 2: A fitness club offers two membership options. Option A has an initial enrollment fee of 75 dollars and a monthly fee of 25 dollars. Option B has no enrollment fee but a monthly fee of 40 dollars. If **C** represents the total cost and **m** represents the number of months, which system of equations can be used to find the number of months after which the total cost of the two options will be the same?\n"
                        "A) **C = 75m + 25**, **C = 40m**\n"
                        "B) **C = 25m + 75**, **C = 40m**\n"
                        "C) **C = 75m + 25**, **C = 40**\n"
                        "D) **C = 25m + 75**, **C = 40m + 0**\n"
                        "Solution: For Option A, the cost starts at 75 dollars and increases by 25 dollars each month, so **C = 25m + 75**. For Option B, there is no initial fee, and the cost increases by 40 dollars each month, so **C = 40m**. Option B matches these two equations. Thus, option B is correct.\n\n"
                        "Use markdown formatting. Do not add any extra sections or preamble."
                        + student_context
                    )
                else:
                    system_instruction = (
                        "You are a concise SAT Reading & Writing tutor. Given an SAT R&W topic name, return a structured card with exactly these sections:\n\n"
                        "**Overview**: One short paragraph (2-3 sentences) explaining what this topic is about and why it appears on the SAT.\n\n"
                        "**Key Rules & Tips**: A numbered list of exactly 5 key grammar rules, rhetorical strategies, or test-taking tips for this topic.\n\n"
                        "**Examples**: Exactly 2 example questions with brief explanations of the correct answer.\n\n"
                        "CRITICAL: Do NOT start with a title, heading, or topic name. Begin immediately with '**Overview**:'. No H1, H2, or H3 markdown headings anywhere in the output.\n\n"
                        "Use markdown formatting. Do not add any extra sections or preamble."
                        + student_context
                    )

                response = call_gemini_with_retry(
                    self.client,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="topic_expander",
                    prompt_chars=len(prompt),
                    response_chars=len(response.text),
                    latency_ms=latency_ms,
                    status="ok"
                )
                return self._strip_heading(response.text)
            except Exception as e:
                latency_ms = int((time.time() - t0) * 1000)
                log_llm_call(
                    agent="topic_expander",
                    prompt_chars=len(prompt),
                    response_chars=0,
                    latency_ms=latency_ms,
                    status="error"
                )
                print(f"DEBUG: Topic Expander live generation failed: {str(e)}")

    @staticmethod
    def _strip_heading(text: str) -> str:
        """Remove any leading H1/H2/H3 markdown heading lines from the card output."""
        if not text:
            return text
        lines = text.splitlines()
        # Drop consecutive leading lines that are headings (# / ## / ###)
        while lines and lines[0].lstrip().startswith("#"):
            lines.pop(0)
        # Also drop any blank lines that follow the removed heading
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines)

        # ─── Fallback Mock Generator ───────────────────────────────────────────
        if is_math:
            if "algebra" in topic_lower or "linear" in topic_lower:
                return (
                    f"**{display_name}** covers equations and relationships that form straight lines when graphed. "
                    "It is one of the most heavily tested topics on the SAT, appearing in both word problem and equation form.\n\n"
                    "**Key Formulas**\n"
                    "1. Slope-Intercept Form: $y = mx + b$\n"
                    "2. Slope: $m = \\dfrac{y_2 - y_1}{x_2 - x_1}$\n"
                    "3. Point-Slope Form: $y - y_1 = m(x - x_1)$\n"
                    "4. Standard Form: $Ax + By = C$\n"
                    "5. Substitution: isolate one variable, substitute into the other equation\n\n"
                    "**Sample Problems**\n"
                    "1. A store sells two types of tickets for a concert: general admission and VIP. A general admission ticket costs 30 dollars, and a VIP ticket costs 75 dollars. On a particular night, the store sold a total of 50 tickets and collected 2,400 dollars in revenue. If **g** represents the number of general admission tickets sold and **v** represents the number of VIP tickets sold, which system of equations represents this situation?\n"
                    "   * **A)** **g + v = 50**, **30g + 75v = 2400**\n"
                    "   * **B)** **g + v = 2400**, **30g + 75v = 50**\n"
                    "   * **C)** **75g + 30v = 50**, **g + v = 2400**\n"
                    "   * **D)** **g + v = 50**, **75g + 30v = 2400**\n\n"
                    "   *Solution:* The total number of tickets sold is 50, so **g + v = 50**. The total revenue is 2,400, and since general admission tickets cost 30 dollars and VIP tickets cost 75 dollars, the revenue equation is **30g + 75v = 2400**. Thus, option A is correct.\n\n"
                    "2. A fitness club offers two membership options. Option A has an initial enrollment fee of 75 dollars and a monthly fee of 25 dollars. Option B has no enrollment fee but a monthly fee of 40 dollars. If **C** represents the total cost and **m** represents the number of months, which system of equations can be used to find the number of months after which the total cost of the two options will be the same?\n"
                    "   * **A)** **C = 75m + 25**, **C = 40m**\n"
                    "   * **B)** **C = 25m + 75**, **C = 40m**\n"
                    "   * **C)** **C = 75m + 25**, **C = 40**\n"
                    "   * **D)** **C = 25m + 75**, **C = 40m + 0**\n\n"
                    "   *Solution:* For Option A, the cost starts at 75 dollars and increases by 25 dollars each month, so **C = 25m + 75**. For Option B, there is no initial fee, and the cost increases by 40 dollars each month, so **C = 40m**. Option B matches these two equations. Thus, option B is correct."
                )
            elif "geometry" in topic_lower or "trig" in topic_lower:
                return (
                    f"**{display_name}** tests your ability to reason about shapes, angles, and spatial relationships. "
                    "SAT geometry problems often involve triangles, circles, and coordinate geometry.\n\n"
                    "**Key Formulas**\n"
                    "1. Pythagorean Theorem: $a^2 + b^2 = c^2$\n"
                    "2. Area of a triangle: $A = \\dfrac{1}{2}bh$\n"
                    "3. Area of a circle: $A = \\pi r^2$\n"
                    "4. Circumference: $C = 2\\pi r$\n"
                    "5. SOHCAHTOA: $\\sin\\theta = \\dfrac{\\text{opp}}{\\text{hyp}}$, $\\cos\\theta = \\dfrac{\\text{adj}}{\\text{hyp}}$\n\n"
                    "**Sample Problems**\n"
                    "1. A right triangle has legs 6 and 8. What is the hypotenuse? *(Answer: 10)*\n"
                    "2. A circle has radius 5. What is its area? *(Answer: $25\\pi$)*"
                )
            elif "quadratic" in topic_lower or "polynomial" in topic_lower:
                return (
                    f"**{display_name}** involves expressions and equations with squared variables. "
                    "SAT problems test factoring, the quadratic formula, and interpreting parabolas.\n\n"
                    "**Key Formulas**\n"
                    "1. Quadratic Formula: $x = \\dfrac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$\n"
                    "2. Standard Form: $ax^2 + bx + c = 0$\n"
                    "3. Vertex Form: $y = a(x - h)^2 + k$\n"
                    "4. Factored Form: $y = a(x - r_1)(x - r_2)$\n"
                    "5. Discriminant: $\\Delta = b^2 - 4ac$ (determines number of solutions)\n\n"
                    "**Sample Problems**\n"
                    "1. Solve $x^2 - 5x + 6 = 0$. *(Answer: $x = 2$ or $x = 3$)*\n"
                    "2. What is the vertex of $y = (x - 3)^2 + 4$? *(Answer: $(3, 4)$)*"
                )
            else:
                return (
                    f"**{display_name}** is an important SAT Math domain that tests conceptual understanding and calculation accuracy. "
                    "Questions in this area require applying core formulas and reasoning through multi-step problems.\n\n"
                    "**Key Formulas**\n"
                    "1. Review all relevant formulas for this domain\n"
                    "2. Identify the key variables in each problem\n"
                    "3. Use unit analysis to check your work\n"
                    "4. Look for shortcuts: plugging in numbers often saves time\n"
                    "5. Eliminate answer choices using estimation when stuck\n\n"
                    "**Sample Problems**\n"
                    "1. Apply the core concept of this topic to a word problem. *(Practice with SAT Khan Academy)*\n"
                    "2. Write out the formula, substitute known values, and solve step by step."
                )
        else:
            if "transition" in topic_lower or "rhetorical" in topic_lower:
                return (
                    f"**{display_name}** tests your ability to select words and phrases that logically connect ideas across sentences. "
                    "These questions appear frequently on the SAT R&W section.\n\n"
                    "**Key Rules & Tips**\n"
                    "1. Read both sentences fully before selecting a transition\n"
                    "2. Identify the logical relationship: contrast, cause/effect, addition, or example\n"
                    "3. *However / Although* = contrast; *Therefore / Thus* = conclusion; *Furthermore* = addition\n"
                    "4. Eliminate transitions that reverse or distort the intended meaning\n"
                    "5. When in doubt, pick the most neutral and precise option\n\n"
                    "**Examples**\n"
                    "1. *The researcher expected strong results. ______, the data showed no significant change.* "
                    "→ Correct: **However** (signals contrast)\n"
                    "2. *She trained every day for six months. ______, she finished the race in record time.* "
                    "→ Correct: **As a result** (signals consequence)"
                )
            elif "punctuation" in topic_lower or "boundary" in topic_lower or "conventions" in topic_lower:
                return (
                    f"**{display_name}** tests your mastery of commas, semicolons, colons, and sentence boundary rules. "
                    "It is one of the most rule-based and consistently tested R&W categories on the SAT.\n\n"
                    "**Key Rules & Tips**\n"
                    "1. A semicolon (;) joins two independent clauses — both sides must be complete sentences\n"
                    "2. A colon (:) introduces a list, explanation, or quotation after an independent clause\n"
                    "3. A comma splice is incorrect: *I studied, I passed* → use a semicolon or conjunction\n"
                    "4. Use a comma before coordinating conjunctions (FANBOYS) joining two independent clauses\n"
                    "5. Non-essential clauses (extra info) are set off with commas; essential ones are not\n\n"
                    "**Examples**\n"
                    "1. *She studied hard, she aced the test.* → Incorrect (comma splice). "
                    "Fix: *She studied hard; she aced the test.*\n"
                    "2. *The scientist who discovered penicillin changed medicine forever.* → No commas needed "
                    "(essential clause identifies which scientist)"
                )
            else:
                return (
                    f"**{display_name}** is a core Reading & Writing topic that tests how well you can analyze and revise academic texts. "
                    "SAT R&W questions in this category reward precision, clarity, and logical reasoning.\n\n"
                    "**Key Rules & Tips**\n"
                    "1. Read the full sentence (and surrounding context) before choosing an answer\n"
                    "2. Eliminate choices that change the intended meaning\n"
                    "3. Prefer the most concise and grammatically correct option\n"
                    "4. Match the tone and register of the surrounding passage\n"
                    "5. If two answers seem correct, choose the one that best fits the passage's argument\n\n"
                    "**Examples**\n"
                    "1. Look for the answer choice that maintains the author's original claim without adding unsupported information.\n"
                    "2. When asked to improve a sentence, check for redundancy, ambiguity, and misplaced modifiers first."
                )