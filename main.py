import os
import requests
import googlemaps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()
GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_HOST") + "/api/chat"
gmaps = googlemaps.Client(key=GMAPS_KEY)
class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.1:8b" # Default model

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_places",
            "description": "Search for places, restaurants, or locations on Google Maps based on user query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query, e.g. 'sate ayam near me' or 'cafe in Jakarta'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

@app.post("/v1/chat")
async def chat_handler(req: ChatRequest):
    payload = {
        "model": req.model,
        "messages": [{"role": "user", "content": req.message}],
        "stream": False,
        "tools": tools_schema 
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response_data = response.json()
        ai_message = response_data.get("message", {})

        if "tool_calls" in ai_message:
            tool_call = ai_message["tool_calls"][0]
            function_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            
            if function_name == "search_places":
                query = arguments.get("query")
                
                print(f"🤖 AI Requesting Map Search for: {query}")
                places_result = gmaps.places(query=query)
                
                if places_result['status'] == 'OK' and places_result['results']:
                    top_places = places_result['results'][:3]
                    results_text = "Here are the places I found on Google Maps:\n"
                    
                    for place in top_places:
                        name = place.get('name')
                        address = place.get('formatted_address')
                        place_id = place.get('place_id')
                        map_link = f"https://www.google.com/maps/search/?api=1&query={name}&query_place_id={place_id}"
                        
                        results_text += f"- **{name}** ({address})\n  [📍 View on Map]({map_link})\n"
                    
                    return {
                        "role": "assistant",
                        "content": results_text,
                        "action": "open_map"
                    }
                else:
                    return {"role": "assistant", "content": "Sorry, I couldn't find that location on Google Maps."}

        return {
            "role": "assistant",
            "content": ai_message.get("content", "")
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check
@app.get("/")
def root():
    return {"status": "running", "service": "AI Maps Recommender"}