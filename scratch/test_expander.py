import sys
import os

# Add project root to sys.path
sys.path.append("/Users/masha/testprep_agent")

from interceptor import process_secure_request

print("--- Testing EXPAND_TOPIC via Interceptor ---")
resp = process_secure_request(
    "EXPAND_TOPIC", 
    "student_001", 
    "valid_token", 
    "valid_token", 
    {"topic_name": "Algebra: Linear equations in one variable - Creating models"}
)

print(f"Status: {resp.get('status')}")
if resp.get("status") == "success":
    print("\n--- Expander Agent Output ---")
    print(resp.get("data"))
else:
    print(f"Error: {resp.get('message')}")
