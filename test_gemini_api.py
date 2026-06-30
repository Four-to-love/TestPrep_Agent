import os
import json
import requests
from dotenv import load_dotenv

def test_gemini_rest_api():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file.")
        return False
        
    api_key = api_key.strip()
    print(f"API Key found: {api_key[:10]}...")
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    # Test 1: Bearer Token Authorization
    print("\n--- TEST 1: Testing Authorization: Bearer header ---")
    headers_bearer = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "contents": [{"parts": [{"text": "Reply with: Bearer Auth Success"}]}]
    }
    
    try:
        response = requests.post(url, headers=headers_bearer, json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Success! Response:\n{response.json()['candidates'][0]['content']['parts'][0]['text'].strip()}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

    # Test 2: Standard x-goog-api-key header
    print("\n--- TEST 2: Testing x-goog-api-key header ---")
    headers_api = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    try:
        response = requests.post(url, headers=headers_api, json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Success!")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")
        
    return False

if __name__ == "__main__":
    test_gemini_rest_api()
