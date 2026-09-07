"""Exposes `retriever_agent` over the A2A protocol as a standalone Starlette app.

Run locally with:
    uvicorn a2a_app:a2a_app --port 8081

Served on Cloud Run with the Dockerfile in this folder.
"""

import os
import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.applications import Starlette
from starlette.routing import Route

from google.adk.a2a.utils.agent_to_a2a import to_a2a

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get deployment settings
PORT = int(os.environ.get("PORT", 8081))
HOST = os.environ.get("HOST", "localhost")
PUBLIC_URL = os.environ.get("PUBLIC_URL")

try:
    logger.info("Importing retriever agent...")
    from agent import root_agent
    logger.info("Retriever agent imported successfully")
except Exception as e:
    logger.error(f"Failed to import retriever agent: {e}", exc_info=True)
    # Create minimal app so container doesn't crash
    async def health(request):
        return JSONResponse({"status": "degraded", "error": str(e)})
    
    base_app = Starlette(routes=[Route("/health", health)])
    root_agent = None

if root_agent:
    try:
        logger.info(f"Creating A2A app on {HOST}:{PORT}")
        base_app = to_a2a(root_agent, host=HOST, port=PORT)
        logger.info("A2A app created successfully")
    except Exception as e:
        logger.error(f"Failed to create A2A app: {e}", exc_info=True)
        async def health(request):
            return JSONResponse({"status": "degraded", "error": str(e)})
        base_app = Starlette(routes=[Route("/health", health)])


class PublicURLMiddleware(BaseHTTPMiddleware):
    """Middleware to fix the agent card RPC URL for Cloud Run deployments."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # If this is the agent card endpoint and we have PUBLIC_URL, fix the RPC URL
        if request.url.path == "/.well-known/agent-card.json" and PUBLIC_URL:
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                agent_card = json.loads(body)
                
                # Replace localhost:8080 with the public URL
                if "supportedInterfaces" in agent_card:
                    for interface in agent_card["supportedInterfaces"]:
                        # Set RPC URL to the PUBLIC_URL
                        interface["url"] = PUBLIC_URL
                
                return JSONResponse(agent_card)
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, return original response
                return response
        
        return response


# Apply middleware if we have a PUBLIC_URL (Cloud Run deployment)
if PUBLIC_URL:
    base_app.add_middleware(PublicURLMiddleware)

# Export the final app
a2a_app = base_app
logger.info(f"Retriever app ready on port {PORT}")
