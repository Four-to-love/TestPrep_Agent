---
name: score-checker
description: Securely fetches chronological past SAT/PSAT score history (Math, RW, and Total) for a student using the local score-checking MCP microservice.
---
# Score Checker Skill

Use this skill when you need to fetch the past SAT or PSAT practice score history of a student.

## Usage
Route requests to the score-checking MCP server using the `fetch_score_history` tool.
- Args: `student_id` (integer).
- Validates the requested student ID against the active session context (denies access to non-session IDs).
