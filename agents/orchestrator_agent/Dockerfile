FROM python:3.12-slim

WORKDIR /app

# Copy orchestrator requirements and install
COPY orchestrator_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator agent code
COPY orchestrator_agent/ .

# Copy BigQuery agent (needed for local import)
COPY bigquery_agent/ /app/bigquery_agent/

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
