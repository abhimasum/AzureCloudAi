"""Exposes `retriever_agent` over the A2A protocol as a standalone Starlette app.

Run locally with:
    uvicorn a2a_app:a2a_app --port 8081

Served on Cloud Run with the Dockerfile in this folder.
"""

import os
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from agent import root_agent

# Get deployment settings
PORT = int(os.environ.get("PORT", 8081))
HOST = os.environ.get("HOST", "localhost")
PUBLIC_URL = os.environ.get("PUBLIC_URL")

# Create the base A2A app
base_app = to_a2a(root_agent, host=HOST, port=PORT)


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
