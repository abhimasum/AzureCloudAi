"""Cloud Run entrypoint for the orchestrator agent.

Serves the same FastAPI app that `adk api_server`/`adk web` use internally, so you get
the ADK dev UI plus the /run and /run_sse endpoints without shelling out to the `adk`
CLI from inside the container.
"""

import os
import sys
import logging

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_WEB_INTERFACE = os.environ.get("SERVE_WEB_INTERFACE", "true").lower() == "true"

try:
    logger.info("Initializing FastAPI app with agents...")
    app = get_fast_api_app(
        agents_dir=AGENT_DIR,
        web=SERVE_WEB_INTERFACE,
        allow_origins=["*"],
    )
    logger.info("FastAPI app initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize FastAPI app: {e}", exc_info=True)
    # Create a minimal app with health check so container doesn't crash
    app = FastAPI()
    
    @app.get("/health")
    async def health():
        return {"status": "degraded", "error": str(e)}
    
    @app.get("/")
    async def root():
        return {"status": "degraded", "error": str(e)}

# Add health check endpoint if not already present
if not hasattr(app, "routes"):
    @app.get("/health")
    async def health():
        return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting uvicorn server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
