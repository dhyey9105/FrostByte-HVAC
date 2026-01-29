import google.generativeai as genai

# Paste your API Key here
api_key = "AIzaSyBPxwuqAVR40W8i8ZkrSXmyzpZI568QPQU" 
genai.configure(api_key=api_key)

print("Checking available AI models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")
    