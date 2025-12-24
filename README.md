# AI Maps Recommendation

This project is a FastAPI-based middleware that integrates a local LLM (via Ollama) with the Google Maps API. It acts as an intelligent agent that can understand user queries about locations (e.g., "Find sate ayam near me") and return structured Google Maps results with ratings, addresses, and direct links.

It exposes an OpenAI-compatible API interface, allowing it to be easily integrated with existing chat frontends.

## Features

- **OpenAI API Compatibility**: Exposes `/v1/chat/completions` and `/v1/models` endpoints.
- **Intelligent Tool Use**: Leverages Llama 3.1's function calling capabilities to decide when to query Google Maps.
- **Real-time Data**: Fetches live data (ratings, reviews, addresses) via the Google Maps Places API.
- **Customizable Backend**: Configurable to point to any Ollama host.

## Prerequisites

- Python 3.9+
- Ollama installed and running.
- The `llama3.1:8b` model pulled in Ollama (`ollama pull llama3.1:8b`).
- A Google Cloud API Key with the **Places API (New)** or **Places API** enabled.

## Installation

1. Clone the repository.
2. Install the required Python packages:

```bash
pip install fastapi uvicorn requests googlemaps
```

## Configuration

The application relies on environment variables for configuration.

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_MAPS_API_KEY` | **Required**. Your Google Maps API Key. | None |
| `OLLAMA_HOST` | The URL of your Ollama instance. | `http://ollama-maps:11434` |

## Usage

1. **Start the Server**:

   ```bash
   export GOOGLE_MAPS_API_KEY="your_actual_api_key"
   # export OLLAMA_HOST="http://localhost:11434" # If running locally
   uvicorn main:app --reload
   ```

2. **Test with cURL**:

   ```bash
   curl -X POST http://127.0.0.1:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "maps-assistant",
       "messages": [
         {"role": "user", "content": "Recommend a sushi place in Tokyo"}
       ]
     }'
   ```

## How It Works

1. **Request**: The user sends a chat message to the FastAPI endpoint.
2. **LLM Processing**: The app forwards the message to Ollama, providing a tool definition for `search_places`.
3. **Decision**:
   - If the LLM decides a search is needed, it returns a "tool call".
   - If not (e.g., "Hello"), it returns normal text.
4. **Execution**:
   - If a tool call is received, the Python app queries the Google Maps API using the `googlemaps` client.
   - The results are formatted into a Markdown list with links and returned as the assistant's response.