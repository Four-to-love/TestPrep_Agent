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
                        "You are an expert SAT Math tutor. Given an SAT Math topic name, return a COMPLETE study block with exactly these sections:\n\n"
                        "**Overview**: One short paragraph (2-3 sentences) explaining what this topic is about and why it appears on the SAT.\n\n"
                        "**Core Formulas**: A comprehensive numbered list of ALL key formulas, identities, and mathematical facts for this topic. "
                        "Include every formula a student must know — aim for 6-10 entries. Use LaTeX inline math notation (e.g. $y = mx + b$). "
                        "Group related formulas together with a brief label explaining when each is used.\n\n"
                        "**Practice Problems**: Exactly 10 SAT-style problems numbered 1–10, covering a full range of difficulty:\n"
                        "  - Problems 1–3: Easy (direct formula application, single-step)\n"
                        "  - Problems 4–6: Medium (two-step reasoning, recognizing the right approach)\n"
                        "  - Problems 7–9: Hard (multi-step, word problems, tricky setups)\n"
                        "  - Problem 10: Challenge (complex, multi-concept, near top-of-test difficulty)\n"
                        "For each problem provide: the question stem (with 4 multiple-choice options A–D where appropriate), "
                        "then '**Solution:**' followed by a concise step-by-step explanation and the correct answer.\n\n"
                        "CRITICAL: Do NOT start with a title, heading, or topic name. Begin immediately with '**Overview**:'. No H1, H2, or H3 markdown headings anywhere in the output.\n\n"
                        "CRITICAL: Never use the dollar sign ($) for currency amounts. Write numbers directly (e.g. write '40 per month' not '$40 per month'). "
                        "Reserve the dollar sign exclusively for LaTeX math expressions like $y = mx + b$.\n\n"
                        "Use markdown formatting. Do not add any extra sections or preamble."
                        + student_context
                    )
                else:
                    system_instruction = (
                        "You are an expert SAT Reading & Writing tutor. Given an SAT R&W topic name, return a COMPLETE study block with exactly these sections:\n\n"
                        "**Overview**: One short paragraph (2-3 sentences) explaining what this topic is about and why it appears on the SAT.\n\n"
                        "**Key Rules & Tips**: A comprehensive numbered list of ALL key grammar rules, rhetorical strategies, and test-taking tips for this topic. "
                        "Include every rule a student must know — aim for 6-10 entries. For each rule, give a brief example or mnemonic.\n\n"
                        "**Practice Problems**: Exactly 10 SAT-style questions numbered 1–10, covering a full range of difficulty:\n"
                        "  - Questions 1–3: Easy (clear rule application, obvious answer)\n"
                        "  - Questions 4–6: Medium (requires careful reading, elimination of close distractors)\n"
                        "  - Questions 7–9: Hard (complex passage context, subtle distinctions)\n"
                        "  - Question 10: Challenge (hardest SAT-style, requires synthesis of multiple rules)\n"
                        "For each question provide: a passage snippet or sentence stem (with 4 answer choices A–D), "
                        "then '**Solution:**' followed by a clear explanation of why the correct answer is right and why the distractors are wrong.\n\n"
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
                    "**Core Formulas**\n"
                    "1. Slope-Intercept Form: $y = mx + b$ (use when slope and y-intercept are known)\n"
                    "2. Slope: $m = \\dfrac{y_2 - y_1}{x_2 - x_1}$ (rise over run between two points)\n"
                    "3. Point-Slope Form: $y - y_1 = m(x - x_1)$ (use when a point and slope are given)\n"
                    "4. Standard Form: $Ax + By = C$ (A, B, C are integers; useful for systems)\n"
                    "5. Substitution Method: isolate one variable, substitute into the other equation\n"
                    "6. Elimination Method: add/subtract equations to cancel one variable\n"
                    "7. Parallel lines: same slope $m$, different $b$\n"
                    "8. Perpendicular lines: slopes are negative reciprocals $m_1 \\cdot m_2 = -1$\n\n"
                    "**Practice Problems**\n\n"
                    "**1. (Easy)** What is the slope of the line $y = 3x - 7$?\n"
                    "A) $-7$ &nbsp; B) $3$ &nbsp; C) $7$ &nbsp; D) $-3$\n"
                    "**Solution:** In slope-intercept form $y = mx + b$, the slope is the coefficient of $x$. Answer: **B) 3**.\n\n"
                    "**2. (Easy)** Which equation represents a line with slope $-2$ and y-intercept $5$?\n"
                    "A) $y = 5x - 2$ &nbsp; B) $y = -2x + 5$ &nbsp; C) $y = 2x + 5$ &nbsp; D) $y = -5x + 2$\n"
                    "**Solution:** Plug $m = -2$, $b = 5$ into $y = mx + b$. Answer: **B) $y = -2x + 5$**.\n\n"
                    "**3. (Easy)** Find the slope of the line passing through $(1, 3)$ and $(3, 7)$.\n"
                    "A) $1$ &nbsp; B) $3$ &nbsp; C) $2$ &nbsp; D) $4$\n"
                    "**Solution:** $m = \\dfrac{7-3}{3-1} = \\dfrac{4}{2} = 2$. Answer: **C) 2**.\n\n"
                    "**4. (Medium)** A line passes through $(-2, 1)$ with slope $3$. What is its equation?\n"
                    "A) $y = 3x + 7$ &nbsp; B) $y = 3x - 5$ &nbsp; C) $y = 3x + 1$ &nbsp; D) $y = 3x - 7$\n"
                    "**Solution:** Using point-slope: $y - 1 = 3(x + 2)$ → $y = 3x + 7$. Answer: **A)**.\n\n"
                    "**5. (Medium)** A store sells general-admission tickets for 30 dollars and VIP tickets for 75 dollars. "
                    "50 tickets are sold totaling 2,400 dollars in revenue. If $g$ = general admission and $v$ = VIP, which system is correct?\n"
                    "A) $g + v = 50$, $30g + 75v = 2400$ &nbsp; B) $g + v = 2400$, $30g + 75v = 50$\n"
                    "C) $75g + 30v = 50$, $g + v = 2400$ &nbsp; D) $g + v = 50$, $75g + 30v = 2400$\n"
                    "**Solution:** Total tickets: $g + v = 50$; total revenue: $30g + 75v = 2400$. Answer: **A)**.\n\n"
                    "**6. (Medium)** At what point do $y = 2x + 1$ and $y = -x + 7$ intersect?\n"
                    "A) $(2, 5)$ &nbsp; B) $(3, 4)$ &nbsp; C) $(1, 3)$ &nbsp; D) $(2, 3)$\n"
                    "**Solution:** Set equal: $2x + 1 = -x + 7$ → $3x = 6$ → $x = 2$, $y = 5$. Answer: **A) $(2, 5)$**.\n\n"
                    "**7. (Hard)** Membership Plan A: 75-dollar enrollment fee plus 25 dollars per month. "
                    "Plan B: no fee, 40 dollars per month. After how many months do costs equalize?\n"
                    "A) $3$ &nbsp; B) $5$ &nbsp; C) $4$ &nbsp; D) $6$\n"
                    "**Solution:** $25m + 75 = 40m$ → $75 = 15m$ → $m = 5$. Answer: **B) 5**.\n\n"
                    "**8. (Hard)** If the lines $3x + ky = 12$ and $6x + 2y = 24$ are the same line, what is $k$?\n"
                    "A) $3$ &nbsp; B) $-3$ &nbsp; C) $1$ &nbsp; D) $2$\n"
                    "**Solution:** For identical lines, coefficients must be proportional. $\\dfrac{6}{3} = \\dfrac{2}{k}$ → $k = 1$. Answer: **C) 1**.\n\n"
                    "**9. (Hard)** A cab charges a flat fee of 3 dollars plus 1.50 dollars per mile. A ride-share charges 0.50 dollars per mile. "
                    "For what number of miles do both services cost the same?\n"
                    "A) $1$ &nbsp; B) $1.5$ &nbsp; C) $2$ &nbsp; D) $3$\n"
                    "**Solution:** $3 + 1.5m = 0.5m$ → $3 = -m$. Re-read: ride-share is 2 dollars plus 0.50/mile. $3 + 1.5m = 2 + 2m$ → $1 = 0.5m$ → $m = 2$. Answer: **C) 2**.\n\n"
                    "**10. (Challenge)** If $ax + by = c$ and $dx + ey = f$ have no solution, which must be true?\n"
                    "A) $\\dfrac{a}{d} = \\dfrac{b}{e} \\neq \\dfrac{c}{f}$ &nbsp; B) $\\dfrac{a}{d} \\neq \\dfrac{b}{e}$ &nbsp; C) $ae = bd$ and $cf = 0$ &nbsp; D) $a = d$ and $b = e$\n"
                    "**Solution:** No solution means parallel lines (same slope, different intercept): $\\dfrac{a}{d} = \\dfrac{b}{e}$ (same direction) but $\\dfrac{a}{d} \\neq \\dfrac{c}{f}$ (different intercept). Answer: **A)**."
                )
            elif "geometry" in topic_lower or "trig" in topic_lower:
                return (
                    f"**{display_name}** tests your ability to reason about shapes, angles, and spatial relationships. "
                    "SAT geometry problems often involve triangles, circles, and coordinate geometry.\n\n"
                    "**Core Formulas**\n"
                    "1. Pythagorean Theorem: $a^2 + b^2 = c^2$ (right triangles)\n"
                    "2. Area of triangle: $A = \\dfrac{1}{2}bh$\n"
                    "3. Area of circle: $A = \\pi r^2$; Circumference: $C = 2\\pi r$\n"
                    "4. SOHCAHTOA: $\\sin\\theta = \\dfrac{\\text{opp}}{\\text{hyp}}$, $\\cos\\theta = \\dfrac{\\text{adj}}{\\text{hyp}}$, $\\tan\\theta = \\dfrac{\\text{opp}}{\\text{adj}}$\n"
                    "5. Special triangles: 30-60-90 sides $x : x\\sqrt{3} : 2x$; 45-45-90 sides $x : x : x\\sqrt{2}$\n"
                    "6. Arc length: $s = r\\theta$ (radians); Sector area: $A = \\dfrac{1}{2}r^2\\theta$\n"
                    "7. Distance formula: $d = \\sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$\n"
                    "8. Midpoint formula: $M = \\left(\\dfrac{x_1+x_2}{2}, \\dfrac{y_1+y_2}{2}\\right)$\n\n"
                    "**Practice Problems**\n\n"
                    "**1. (Easy)** A right triangle has legs 6 and 8. What is the hypotenuse?\n"
                    "A) 10 &nbsp; B) 12 &nbsp; C) 14 &nbsp; D) 9\n"
                    "**Solution:** $6^2 + 8^2 = 36 + 64 = 100$; $\\sqrt{100} = 10$. Answer: **A) 10**.\n\n"
                    "**2. (Easy)** A circle has radius 5. What is its area?\n"
                    "A) $10\\pi$ &nbsp; B) $25\\pi$ &nbsp; C) $5\\pi$ &nbsp; D) $50\\pi$\n"
                    "**Solution:** $A = \\pi(5)^2 = 25\\pi$. Answer: **B) $25\\pi$**.\n\n"
                    "**3. (Easy)** What is the distance between $(1, 2)$ and $(4, 6)$?\n"
                    "A) $4$ &nbsp; B) $5$ &nbsp; C) $6$ &nbsp; D) $7$\n"
                    "**Solution:** $d = \\sqrt{(4-1)^2+(6-2)^2} = \\sqrt{9+16} = 5$. Answer: **B) 5**.\n\n"
                    "**4. (Medium)** In a 30-60-90 triangle, the shortest side is 4. What is the hypotenuse?\n"
                    "A) $4\\sqrt{3}$ &nbsp; B) $8$ &nbsp; C) $4\\sqrt{2}$ &nbsp; D) $6$\n"
                    "**Solution:** Hypotenuse = $2x = 2(4) = 8$. Answer: **B) 8**.\n\n"
                    "**5. (Medium)** $\\sin(30°) = ?$\n"
                    "A) $\\dfrac{\\sqrt{3}}{2}$ &nbsp; B) $\\dfrac{1}{2}$ &nbsp; C) $1$ &nbsp; D) $\\dfrac{\\sqrt{2}}{2}$\n"
                    "**Solution:** In a 30-60-90 triangle, $\\sin(30°) = \\dfrac{1}{2}$. Answer: **B)**.\n\n"
                    "**6. (Medium)** A sector of a circle with radius 6 has a central angle of 60°. What is the area of the sector?\n"
                    "A) $6\\pi$ &nbsp; B) $3\\pi$ &nbsp; C) $12\\pi$ &nbsp; D) $36\\pi$\n"
                    "**Solution:** $A = \\dfrac{60}{360} \\cdot \\pi(6)^2 = \\dfrac{1}{6} \\cdot 36\\pi = 6\\pi$. Answer: **A) $6\\pi$**.\n\n"
                    "**7. (Hard)** A ladder 10 feet long leans against a wall. Its base is 6 feet from the wall. How high up the wall does it reach?\n"
                    "A) $6$ &nbsp; B) $8$ &nbsp; C) $9$ &nbsp; D) $7$\n"
                    "**Solution:** $h = \\sqrt{10^2 - 6^2} = \\sqrt{64} = 8$. Answer: **B) 8**.\n\n"
                    "**8. (Hard)** A circle is inscribed in a square with side 8. What is the area of the region inside the square but outside the circle?\n"
                    "A) $64 - 16\\pi$ &nbsp; B) $64 - 4\\pi$ &nbsp; C) $32 - 16\\pi$ &nbsp; D) $16 - 8\\pi$\n"
                    "**Solution:** Radius = 4; circle area = $16\\pi$; square area = $64$; difference = $64 - 16\\pi$. Answer: **A)**.\n\n"
                    "**9. (Hard)** In right triangle $ABC$ with right angle at $C$, $\\tan(A) = \\dfrac{3}{4}$. What is $\\sin(A)$?\n"
                    "A) $\\dfrac{3}{5}$ &nbsp; B) $\\dfrac{4}{5}$ &nbsp; C) $\\dfrac{3}{4}$ &nbsp; D) $\\dfrac{4}{3}$\n"
                    "**Solution:** Opposite = 3, adjacent = 4; hypotenuse = $\\sqrt{9+16} = 5$. $\\sin(A) = \\dfrac{3}{5}$. Answer: **A)**.\n\n"
                    "**10. (Challenge)** A point $P$ is on the circle $x^2 + y^2 = 25$. The line through $P$ and the origin makes a 45° angle with the x-axis. What are the coordinates of $P$ in quadrant I?\n"
                    "A) $(3, 4)$ &nbsp; B) $(\\dfrac{5\\sqrt{2}}{2}, \\dfrac{5\\sqrt{2}}{2})$ &nbsp; C) $(4, 3)$ &nbsp; D) $(5, 0)$\n"
                    "**Solution:** At 45°, $x = y$; substituting: $2x^2 = 25$ → $x = \\dfrac{5}{\\sqrt{2}} = \\dfrac{5\\sqrt{2}}{2}$. Answer: **B)**."
                )
            elif "quadratic" in topic_lower or "polynomial" in topic_lower:
                return (
                    f"**{display_name}** involves expressions and equations with squared variables. "
                    "SAT problems test factoring, the quadratic formula, and interpreting parabolas.\n\n"
                    "**Core Formulas**\n"
                    "1. Quadratic Formula: $x = \\dfrac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$\n"
                    "2. Standard Form: $ax^2 + bx + c = 0$\n"
                    "3. Vertex Form: $y = a(x - h)^2 + k$ — vertex at $(h, k)$\n"
                    "4. Factored Form: $y = a(x - r_1)(x - r_2)$ — roots at $r_1$ and $r_2$\n"
                    "5. Discriminant: $\\Delta = b^2 - 4ac$ — positive → 2 real roots; zero → 1 repeated root; negative → no real roots\n"
                    "6. Sum of roots: $r_1 + r_2 = -\\dfrac{b}{a}$; Product of roots: $r_1 r_2 = \\dfrac{c}{a}$\n"
                    "7. Completing the square: $x^2 + bx = \\left(x + \\dfrac{b}{2}\\right)^2 - \\dfrac{b^2}{4}$\n\n"
                    "**Practice Problems**\n\n"
                    "**1. (Easy)** Solve $x^2 - 5x + 6 = 0$.\n"
                    "A) $x = 1, 6$ &nbsp; B) $x = 2, 3$ &nbsp; C) $x = -2, -3$ &nbsp; D) $x = 0, 5$\n"
                    "**Solution:** Factor: $(x-2)(x-3)=0$ → $x=2$ or $x=3$. Answer: **B)**.\n\n"
                    "**2. (Easy)** What is the vertex of $y = (x-3)^2 + 4$?\n"
                    "A) $(3, 4)$ &nbsp; B) $(-3, 4)$ &nbsp; C) $(3, -4)$ &nbsp; D) $(4, 3)$\n"
                    "**Solution:** Vertex form $y = a(x-h)^2 + k$ gives vertex $(h, k) = (3, 4)$. Answer: **A)**.\n\n"
                    "**3. (Easy)** How many real solutions does $x^2 + 4 = 0$ have?\n"
                    "A) $0$ &nbsp; B) $1$ &nbsp; C) $2$ &nbsp; D) $4$\n"
                    "**Solution:** $x^2 = -4$ — no real solution (negative under square root). Answer: **A) 0**.\n\n"
                    "**4. (Medium)** Solve $2x^2 - 4x - 6 = 0$.\n"
                    "A) $x = 1, -3$ &nbsp; B) $x = -1, 3$ &nbsp; C) $x = 3, -1$ &nbsp; D) $x = 2, -3$\n"
                    "**Solution:** Divide by 2: $x^2 - 2x - 3 = 0$ → $(x-3)(x+1) = 0$ → $x = 3$ or $x = -1$. Answer: **C)**.\n\n"
                    "**5. (Medium)** For what values of $x$ does $x^2 - 6x + 9 = 0$?\n"
                    "A) $x = 3$ only &nbsp; B) $x = \\pm 3$ &nbsp; C) $x = 0, 6$ &nbsp; D) $x = -3$ only\n"
                    "**Solution:** $(x-3)^2 = 0$ → $x = 3$ (double root). Answer: **A)**.\n\n"
                    "**6. (Medium)** A parabola has roots at $x = -1$ and $x = 5$ and opens upward. Which best describes its vertex?\n"
                    "A) minimum at $x = 2$ &nbsp; B) maximum at $x = 2$ &nbsp; C) minimum at $x = -1$ &nbsp; D) maximum at $x = 5$\n"
                    "**Solution:** Vertex x-coordinate = midpoint of roots = $\\dfrac{-1+5}{2} = 2$; parabola opens up → minimum. Answer: **A)**.\n\n"
                    "**7. (Hard)** Use the quadratic formula to solve $3x^2 + 2x - 1 = 0$.\n"
                    "A) $x = \\dfrac{1}{3}$ or $x = -1$ &nbsp; B) $x = 1$ or $x = \\dfrac{-1}{3}$ &nbsp; C) $x = \\dfrac{2}{3}$ or $x = -1$ &nbsp; D) no real solution\n"
                    "**Solution:** $\\Delta = 4 + 12 = 16$; $x = \\dfrac{-2 \\pm 4}{6}$ → $x = \\dfrac{1}{3}$ or $x = -1$. Answer: **A)**.\n\n"
                    "**8. (Hard)** The product of two consecutive integers is 56. Which quadratic models this?\n"
                    "A) $n^2 + n - 56 = 0$ &nbsp; B) $n^2 - n - 56 = 0$ &nbsp; C) $n^2 + 2n - 56 = 0$ &nbsp; D) $n^2 - 56 = 0$\n"
                    "**Solution:** Consecutive integers: $n(n+1) = 56$ → $n^2 + n - 56 = 0$. Answer: **A)**.\n\n"
                    "**9. (Hard)** For $kx^2 - 6x + 3 = 0$ to have exactly one solution, what must $k$ equal?\n"
                    "A) $1$ &nbsp; B) $2$ &nbsp; C) $3$ &nbsp; D) $4$\n"
                    "**Solution:** $\\Delta = 0$: $36 - 12k = 0$ → $k = 3$. Answer: **C) 3**.\n\n"
                    "**10. (Challenge)** If $p$ and $q$ are roots of $x^2 - 5x + 3 = 0$, what is $p^2 + q^2$?\n"
                    "A) $19$ &nbsp; B) $25$ &nbsp; C) $9$ &nbsp; D) $13$\n"
                    "**Solution:** $p + q = 5$, $pq = 3$; $p^2 + q^2 = (p+q)^2 - 2pq = 25 - 6 = 19$. Answer: **A) 19**."
                )
            else:
                return (
                    f"**{display_name}** is an important SAT Math domain that tests conceptual understanding and calculation accuracy. "
                    "Questions in this area require applying core formulas and reasoning through multi-step problems.\n\n"
                    "**Core Formulas**\n"
                    "1. Review all relevant formulas for this domain\n"
                    "2. Identify the key variables in each problem\n"
                    "3. Use unit analysis to check your work\n"
                    "4. Look for shortcuts: plugging in numbers often saves time\n"
                    "5. Eliminate answer choices using estimation when stuck\n\n"
                    "**Practice Problems** *(generated by AI — expand the topic above to load live problems)*\n\n"
                    "**1. (Easy)** Apply the most basic formula for this topic directly.\n"
                    "**Solution:** Identify the known values, substitute into the formula, and solve.\n\n"
                    "**2–10.** Practice with SAT Khan Academy or re-expand this topic for full AI-generated problems."
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
                    "5. When in doubt, pick the most neutral and precise option\n"
                    "6. *For example / For instance* = introduces evidence; *In contrast* = reversal\n"
                    "7. *Similarly / Likewise* = comparison; *Consequently / As a result* = effect\n\n"
                    "**Practice Problems**\n\n"
                    "**1. (Easy)** *The study was small. ______, its conclusions may not apply to all populations.*\n"
                    "A) Furthermore &nbsp; B) Therefore &nbsp; C) However &nbsp; D) Similarly\n"
                    "**Solution:** The second sentence limits the first → contrast. Answer: **C) However**.\n\n"
                    "**2. (Easy)** *She trained every day. ______, she finished the race in record time.*\n"
                    "A) In contrast &nbsp; B) As a result &nbsp; C) However &nbsp; D) For instance\n"
                    "**Solution:** Training caused the record time → cause/effect. Answer: **B) As a result**.\n\n"
                    "**3. (Easy)** *The researcher expected strong results. ______, the data showed no significant change.*\n"
                    "A) Therefore &nbsp; B) Furthermore &nbsp; C) However &nbsp; D) Similarly\n"
                    "**Solution:** Expectation vs. reality → contrast. Answer: **C) However**.\n\n"
                    "**4. (Medium)** *The novel is widely praised for its prose style. ______, critics have noted its slow pacing.*\n"
                    "A) As a result &nbsp; B) Similarly &nbsp; C) Nevertheless &nbsp; D) Therefore\n"
                    "**Solution:** Praise but also criticism → concessive contrast. Answer: **C) Nevertheless**.\n\n"
                    "**5. (Medium)** *Many ancient civilizations developed writing independently. ______, the Sumerians, Egyptians, and Chinese each created distinct scripts.*\n"
                    "A) However &nbsp; B) For example &nbsp; C) As a result &nbsp; D) Conversely\n"
                    "**Solution:** The second sentence gives examples of the first claim. Answer: **B) For example**.\n\n"
                    "**6. (Medium)** *The software update improved security. ______, several key features were removed.*\n"
                    "A) Furthermore &nbsp; B) Consequently &nbsp; C) However &nbsp; D) Similarly\n"
                    "**Solution:** Improvement is offset by a loss → contrast/concession. Answer: **C) However**.\n\n"
                    "**7. (Hard)** *Proponents argue the policy will reduce costs. Opponents contend it will reduce quality. ______, a full cost-benefit analysis is needed.*\n"
                    "A) In contrast &nbsp; B) For example &nbsp; C) Given this debate &nbsp; D) Similarly\n"
                    "**Solution:** Both sides are presented; the conclusion follows logically → synthesis. Answer: **C) Given this debate**.\n\n"
                    "**8. (Hard)** *The author concedes that early prototypes failed. ______, she argues the final design overcame all previous limitations.*\n"
                    "A) Therefore &nbsp; B) Nevertheless &nbsp; C) For instance &nbsp; D) Conversely\n"
                    "**Solution:** Concedes a problem but asserts it was resolved → concessive. Answer: **B) Nevertheless**.\n\n"
                    "**9. (Hard)** *Coral reefs support extraordinary biodiversity. ______, they protect coastlines from storm surges.*\n"
                    "A) However &nbsp; B) In addition &nbsp; C) Consequently &nbsp; D) For example\n"
                    "**Solution:** A second benefit is added to the first → addition. Answer: **B) In addition**.\n\n"
                    "**10. (Challenge)** *The philosopher maintained that moral truths are universal. Her critics, ______, insisted that ethics are culturally constructed and therefore variable.*\n"
                    "A) similarly &nbsp; B) in contrast &nbsp; C) consequently &nbsp; D) as a result\n"
                    "**Solution:** The critics hold the opposing view to the philosopher → contrast. Answer: **B) in contrast**."
                )
            elif "punctuation" in topic_lower or "boundary" in topic_lower or "conventions" in topic_lower:
                return (
                    f"**{display_name}** tests your mastery of commas, semicolons, colons, and sentence boundary rules. "
                    "It is one of the most rule-based and consistently tested R&W categories on the SAT.\n\n"
                    "**Key Rules & Tips**\n"
                    "1. A semicolon (;) joins two independent clauses — both sides must be complete sentences\n"
                    "2. A colon (:) introduces a list, explanation, or quotation after an independent clause\n"
                    "3. A comma splice is incorrect: *I studied, I passed* → use a semicolon or conjunction\n"
                    "4. Use a comma before coordinating conjunctions (FANBOYS: for, and, nor, but, or, yet, so) joining two independent clauses\n"
                    "5. Non-essential clauses (extra info) are set off with commas; essential ones are not\n"
                    "6. A dash (—) can replace a colon or set off a parenthetical with more emphasis\n"
                    "7. Do NOT use a comma between a subject and its verb\n\n"
                    "**Practice Problems**\n\n"
                    "**1. (Easy)** *She studied hard, she aced the test.* What is wrong?\n"
                    "A) No error &nbsp; B) Comma splice &nbsp; C) Missing colon &nbsp; D) Wrong semicolon\n"
                    "**Solution:** Two independent clauses joined by only a comma = comma splice. Answer: **B)**.\n\n"
                    "**2. (Easy)** Which punctuation correctly joins the clauses: *The sun set [?] the stars appeared.*\n"
                    "A) comma only &nbsp; B) semicolon &nbsp; C) colon &nbsp; D) no punctuation\n"
                    "**Solution:** Both sides are complete sentences → semicolon. Answer: **B)**.\n\n"
                    "**3. (Easy)** *The scientist who discovered penicillin changed medicine forever.* Should commas surround 'who discovered penicillin'?\n"
                    "A) Yes, it's non-essential &nbsp; B) No, it's essential &nbsp; C) Yes, it's a transition &nbsp; D) No, it's a verb phrase\n"
                    "**Solution:** The clause identifies which scientist → essential → no commas. Answer: **B)**.\n\n"
                    "**4. (Medium)** *The team had one goal[?] to win the championship.* Which punctuation fits the bracket?\n"
                    "A) comma &nbsp; B) semicolon &nbsp; C) colon &nbsp; D) dash\n"
                    "**Solution:** An independent clause introduces an explanation → colon. (Dash also acceptable, but colon is most standard.) Answer: **C)**.\n\n"
                    "**5. (Medium)** *Maria, who is my neighbor, bakes excellent bread.* Are the commas correct?\n"
                    "A) Yes, the clause is non-essential &nbsp; B) No, the clause is essential &nbsp; C) No, use semicolons &nbsp; D) Yes, FANBOYS rule applies\n"
                    "**Solution:** 'Who is my neighbor' adds extra info, not needed to identify Maria → non-essential → commas correct. Answer: **A)**.\n\n"
                    "**6. (Medium)** *He wanted to travel but he had no money.* Is punctuation needed before 'but'?\n"
                    "A) No, 'but' alone is sufficient &nbsp; B) Yes, a comma before 'but' &nbsp; C) Yes, a semicolon before 'but' &nbsp; D) Yes, a colon before 'but'\n"
                    "**Solution:** Two independent clauses joined by FANBOYS conjunction → comma before 'but'. Answer: **B)**.\n\n"
                    "**7. (Hard)** *The exhibit featured three artists[?] Kahlo, Basquiat, and Warhol.* Choose the correct punctuation.\n"
                    "A) comma &nbsp; B) semicolon &nbsp; C) colon &nbsp; D) em dash\n"
                    "**Solution:** Independent clause before a list → colon. Answer: **C)**.\n\n"
                    "**8. (Hard)** Choose the correctly punctuated sentence.\n"
                    "A) *Running every morning, builds stamina.* &nbsp; B) *Running every morning builds stamina.* &nbsp; "
                    "C) *Running, every morning builds stamina.* &nbsp; D) *Running every morning; builds stamina.*\n"
                    "**Solution:** The subject is 'Running every morning' — no comma should separate it from the verb. Answer: **B)**.\n\n"
                    "**9. (Hard)** *The delegation arrived on Monday however the talks did not begin until Wednesday.* Identify the error.\n"
                    "A) Missing comma after 'Monday' &nbsp; B) Comma splice &nbsp; C) Missing semicolon after 'Monday' and comma after 'however' &nbsp; D) No error\n"
                    "**Solution:** 'However' is a conjunctive adverb — needs a semicolon before and comma after: *Monday; however, the talks...*. Answer: **C)**.\n\n"
                    "**10. (Challenge)** Which version is correctly punctuated?\n"
                    "A) *The report, that was submitted late, was still accepted.* &nbsp; "
                    "B) *The report that was submitted late was still accepted.* &nbsp; "
                    "C) *The report that was submitted late, was still accepted.* &nbsp; "
                    "D) *The report, that was submitted late was still accepted.*\n"
                    "**Solution:** 'That was submitted late' is a restrictive (essential) relative clause identifying which report — no commas. Answer: **B)**."
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
                    "5. If two answers seem correct, choose the one that best fits the passage's argument\n"
                    "6. 'LEAST acceptable' and 'EXCEPT' questions: find the one that breaks the rule\n"
                    "7. For 'complete the text' questions, match the logical flow of surrounding sentences\n\n"
                    "**Practice Problems** *(generated by AI — expand the topic above to load live problems)*\n\n"
                    "**1. (Easy)** Choose the most grammatically correct and concise option.\n"
                    "**Solution:** Eliminate redundant or ambiguous choices; prefer the clearest sentence.\n\n"
                    "**2–10.** Practice with SAT Khan Academy or re-expand this topic for full AI-generated problems."
                )