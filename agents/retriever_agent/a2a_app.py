"""FastAPI app exposing `retriever_agent` over HTTP, called by the orchestrator agent.

Run locally with:
    uvicorn a2a_app:a2a_app --port 8081

Served on Azure Container Apps with the Dockerfile in this folder.
"""

import logging

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

a2a_app = FastAPI()
root_agent = None
_init_error = None

try:
    logger.info("Initializing retriever agent...")
    from agent import root_agent
    logger.info("Retriever agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize retriever agent: {e}", exc_info=True)
    _init_error = str(e)


class RunRequest(BaseModel):
    query: str


@a2a_app.get("/health")
async def health():
    if root_agent is None:
        return {"status": "degraded", "error": _init_error}
    return {"status": "ok"}


@a2a_app.get("/")
async def root():
    return await health()


@a2a_app.post("/run")
async def run(request: RunRequest):
    if root_agent is None:
        return {"response": f"Agent not initialized: {_init_error}"}
    result = await root_agent.run(request.query)
    return {"response": str(result)}
