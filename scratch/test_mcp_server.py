import os
import sys

# Add project root to sys.path
sys.path.append("/Users/masha/testprep_agent")

from mcp_server import fetch_score_history

print("--- Testing fetch_score_history with student_id = 1 (Active Session) ---")
res_valid = fetch_score_history(1)
print(res_valid)

print("\n--- Testing fetch_score_history with student_id = 2 (Unauthorized Session) ---")
res_unauth = fetch_score_history(2)
print(res_unauth)

print("\n--- Testing fetch_score_history with student_id = 'not-an-int' (Validation Error) ---")
res_invalid = fetch_score_history("not-an-int")
print(res_invalid)
