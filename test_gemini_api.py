import os
import json
import requests
from dotenv import load_dotenv

def test_gemini_rest_api():
    # Load environment variables from .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env file.")
        return False
        
    print("API Key found. Testing native REST endpoint using x-goog-api-key header...")
    
    # Native REST API endpoint for Gemini
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    # Headers using x-goog-api-key
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key.strip()
    }
    
    # Standard Gemini JSON payload structure
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello, this is a system test. Please reply exactly with the phrase: 'API Connection Successful!'"}
                ]
            }
        ]
    }
    
    try:
        print(f"Sending POST request to {url}...")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            try:
                reply = data['candidates'][0]['content']['parts'][0]['text']
                print(f"\n✅ SUCCESS! Received response:\n{reply.strip()}")
                return True
            except KeyError:
                print(f"\n⚠️ SUCCESSFUL connection (200), but unexpected response format:\n{json.dumps(data, indent=2)}")
                return True
        else:
            print(f"\n❌ FAILED. Status Code: {response.status_code}")
            print(f"Error Details:\n{response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPTION occurred during request: {str(e)}")
        return False

if __name__ == "__main__":
    test_gemini_rest_api()
