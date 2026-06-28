# Description
Use this skill ONLY when the user asks about National Merit Selection Index (NMSI) thresholds, state cutoffs, or PSAT target scores. 

# Goal
Calculate the student's NMSI based on their practice scores and compare it against historical state cutoffs to provide actionable feedback.

# Instructions
1. When a user asks about their National Merit standing, immediately read the logic inside `nmsi_calculator.py` located in this skill's directory.
2. If the user has not provided their Math and Reading/Writing (R/W) scores, politely ask for them.
3. Use the Python script to calculate the NMSI: `((2 * RW) + Math) / 10`.
4. Use the Python script to look up the target cutoff for their specific US State. 
5. Tell the student exactly how many points they are away from their state's target.

# Constraints
- Do NOT hallucinate cutoffs for states not listed in the script's dictionary. If a state is missing, clearly state that the default target of 220 is being used.
- Do NOT explain the math formula to the user unless they explicitly ask how the NMSI is calculated.
- Keep the tone encouraging but highly analytical.