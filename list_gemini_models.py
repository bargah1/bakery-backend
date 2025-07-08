import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Configured Gemini API key. Listing models...")
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"Model: {m.name}, Supported methods: {m.supported_generation_methods}")
    except Exception as e:
        print(f"Error listing models: {e}")