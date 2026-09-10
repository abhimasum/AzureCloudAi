"""FastAPI entrypoint for the orchestrator agent, serving it over HTTP with MAF."""

import os
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
root_agent = None
_init_error = None

try:
    logger.info("Initializing orchestrator agent...")
    from agent import root_agent
    logger.info("Orchestrator agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize orchestrator agent: {e}", exc_info=True)
    _init_error = str(e)


class Message(BaseModel):
    role: str  # "user" or "bot"
    content: str


class RunRequest(BaseModel):
    query: str
    context: list[Message] = []  # Conversation history for context


@app.get("/health")
async def health():
    if root_agent is None:
        return {"status": "degraded", "error": _init_error}
    return {"status": "ok"}


@app.get("/")
async def root():
    """Serve the chat UI"""
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return await health()


@app.post("/run")
async def run(request: RunRequest):
    if root_agent is None:
        return {"response": f"Agent not initialized: {_init_error}"}
    
    try:
        # Build context string from conversation history
        context_str = ""
        if request.context:
            context_str = "Conversation history:\n"
            for msg in request.context:
                context_str += f"{msg.role}: {msg.content}\n"
            context_str += "\nCurrent query: "
        
        # Combine context with current query
        full_query = context_str + request.query if context_str else request.query
        
        result = await root_agent.run(full_query)
        
        # Extract content from response object
        # agent_framework returns a response object with choices
        response_text = str(result)
        if hasattr(result, 'choices') and result.choices:
            response_text = result.choices[0].message.content
        
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return {"response": f"Error: {str(e)}", "error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting uvicorn server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
