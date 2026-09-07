"""FastAPI entrypoint for the orchestrator agent, serving it over HTTP with MAF."""

import os
import logging

import uvicorn
from fastapi import FastAPI
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


class RunRequest(BaseModel):
    query: str


@app.get("/health")
async def health():
    if root_agent is None:
        return {"status": "degraded", "error": _init_error}
    return {"status": "ok"}


@app.get("/")
async def root():
    return await health()


@app.post("/run")
async def run(request: RunRequest):
    if root_agent is None:
        return {"response": f"Agent not initialized: {_init_error}"}
    result = await root_agent.run(request.query)
    return {"response": str(result)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting uvicorn server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
