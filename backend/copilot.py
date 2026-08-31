import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def ask_copilot(user_message: str, optimal_schedule: dict, live_state: dict = None) -> str:
    """
    Sends the user's question, schedule, and live state to Gemma via REST API.
    """
    if not GOOGLE_API_KEY:
        return "Copilot is currently offline. Please add your GOOGLE_API_KEY to the .env file."

    context_str = ""
    if "schedule" in optimal_schedule:
        context_str += f"AI Optimizer Reason: {optimal_schedule.get('reason', 'N/A')}\n"
        context_str += f"Baseline Metrics: {optimal_schedule.get('baseline', 'N/A')}\n"
        context_str += f"Optimized Metrics: {optimal_schedule.get('optimized', 'N/A')}\n"
        context_str += f"Schedule Snapshot: {str(optimal_schedule['schedule'][:3])}\n"
    else:
        context_str += "Optimization Schedule: Not available.\n"
        
    live_str = str(live_state) if live_state else "No live data available."

    import re
    
    import json
    import re

    # Force Gemma to output a JSON code block
    full_prompt = f"""You are the EcoGrid AI Assistant. You must answer the user's question directly in a friendly 2-3 sentence paragraph. 
You MUST output your final answer inside a markdown JSON code block like this:
```json
{{"response": "Your friendly answer goes here."}}
```

Live Grid Telemetry: {live_str}
{context_str}
User Question: {user_message}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Safely extract the JSON block
        match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                json_data = json.loads(match.group(1))
                return json_data.get("response", raw_text)
            except:
                pass
                
        # Super fallback if it forgets the code block but uses quotes
        quote_match = re.findall(r'"([^"]{20,})"', raw_text)
        if quote_match:
            return quote_match[-1]
            
        return raw_text.strip()
    except Exception as e:
        return f"Error communicating with Google AI Studio: {str(e)}"
