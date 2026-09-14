FROM python:3.12-slim

WORKDIR /app

# ODBC Driver 18 required by pyodbc (sql_agent, imported as a sibling package)
# Also install build essentials for package compilation
RUN apt-get update && apt-get install -y \
    curl gnupg apt-transport-https \
    build-essential python3-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update --allow-unauthenticated \
    && ACCEPT_EULA=Y apt-get install -y --allow-unauthenticated msodbcsql18 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install basic dependencies
RUN pip install --upgrade pip setuptools wheel --no-cache-dir

# Copy orchestrator requirements and install with verbose output for debugging
COPY orchestrator_agent/requirements.txt .
RUN echo "Installing Python dependencies..." && \
    pip install --no-cache-dir -r requirements.txt --verbose 2>&1 | tail -50 || \
    (echo "First attempt failed, retrying with compatible versions..." && \
     pip install --no-cache-dir \
       agent-framework==1.16.0 \
       agent-framework-openai==1.14.0 \
       azure-identity>=1.15.0 \
       azure-ai-projects>=1.0.0 \
       azure-cosmos>=4.5.0 \
       azure-ai-inference>=1.0.0 \
       uvicorn>=0.27.0 \
       fastapi>=0.109.0 \
       httpx>=0.27.0 \
       openai>=1.0.0)

# Copy orchestrator agent code (includes static folder), plus sql_agent (imported as a sibling package)
COPY orchestrator_agent/ .
COPY sql_agent/ ./sql_agent/

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
