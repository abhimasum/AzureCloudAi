"""HTTP wrapper around ingest.py so Cloud Scheduler can trigger re-ingestion.

Cloud Scheduler should call this with a POST request using an OIDC identity token
(see infra/setup_gcp.sh and .github/workflows/deploy.yml) — do not deploy this service
with --allow-unauthenticated.
"""

import logging
import os

from flask import Flask
from flask import jsonify

from ingest import run_ingestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/", methods=["POST", "GET"])
def trigger_ingestion():
    try:
        corpus_name = run_ingestion()
        return jsonify({"status": "ok", "rag_corpus": corpus_name}), 200
    except Exception as exc:  # noqa: BLE001 - surface any failure to the caller/logs
        logger.exception("Ingestion failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
