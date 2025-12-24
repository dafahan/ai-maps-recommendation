import os
import time
import uuid
import requests
import googlemaps
import urllib.parse  
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-maps:11434")
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
VIRTUAL_MODEL_ID = "maps-assistant"
ACTUAL_OLLAMA_MODEL = "llama3.1:8b"

try:
    if GMAPS_KEY:
        gmaps = googlemaps.Client(key=GMAPS_KEY)
    else:
        gmaps = None
except Exception:
    gmaps = None

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = VIRTUAL_MODEL_ID
    messages: List[Message] 
    stream: bool = False

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
                        "description": "The search query, e.g. 'sate ayam near me'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

@app.get("/")
def root():
    return {"status": "AI Maps Recommender Ready", "model_id": VIRTUAL_MODEL_ID}

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": VIRTUAL_MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "custom-maps-backend",
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_handler(req: ChatRequest):
    last_user_message = req.messages[-1].content
    
    payload = {
        "model": ACTUAL_OLLAMA_MODEL, 
        "messages": [{"role": "user", "content": last_user_message}],
        "stream": False,
        "tools": tools_schema 
    }

    final_content = ""

    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ollama Error: {response.text}")

        response_data = response.json()
        ai_message = response_data.get("message", {})

        if "tool_calls" in ai_message:
            tool_call = ai_message["tool_calls"][0]
            function_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            
            if function_name == "search_places" and gmaps:
                query = arguments.get("query")
                
                places_result = gmaps.places(query=query)
                
                if places_result['status'] == 'OK' and places_result['results']:
                    top_places = places_result['results'][:5]
                    
                    results_text = f"### 🗺️ Search Results for: '{query}'\n\n"
                    
                    for i, place in enumerate(top_places, 1):
                        name = place.get('name')
                        address = place.get('formatted_address')
                        place_id = place.get('place_id')
                        rating = place.get('rating', 'N/A')
                        user_ratings_total = place.get('user_ratings_total', 0)

                        safe_name = urllib.parse.quote(name)
                        map_link = f"https://www.google.com/maps/search/?api=1&query={safe_name}&query_place_id={place_id}"
                        
                        results_text += f"**{i}. {name}** (⭐ {rating} | {user_ratings_total} reviews)\n"
                        results_text += f"   📍 _{address}_\n"
                        results_text += f"   🔗 [Open in Google Maps]({map_link})\n\n"
                        results_text += "---\n\n" 
                    
                    final_content = results_text
                else:
                    final_content = f"Sorry, I searched Google Maps for '{query}' but couldn't find any matching results."
            elif not gmaps:
                final_content = "Sorry, Google Maps API Key is missing or invalid."
            else:
                 final_content = "Sorry, map search is currently unavailable."
        
        else:
            final_content = ai_message.get("content", "")

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0, 
                "completion_tokens": 0, 
                "total_tokens": 0
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))