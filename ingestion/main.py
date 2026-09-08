"""HTTP wrapper around ingest.py to trigger document ingestion into Azure AI Search.

Azure Container Apps Job or Timer-triggered Function should call this with a POST request.
For testing, can be called manually via curl or browser.
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
