"""Cloud Run entrypoint for the orchestrator agent.

Serves the same FastAPI app that `adk api_server`/`adk web` use internally, so you get
the ADK dev UI plus the /run and /run_sse endpoints without shelling out to the `adk`
CLI from inside the container.
"""

import os

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVE_WEB_INTERFACE = os.environ.get("SERVE_WEB_INTERFACE", "true").lower() == "true"

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=SERVE_WEB_INTERFACE,
    allow_origins=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
