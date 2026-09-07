FROM python:3.12-slim

WORKDIR /app

# ODBC Driver 18 required by pyodbc (sql_agent, imported as a sibling package)
RUN apt-get update && apt-get install -y curl gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc \
    && curl https://packages.microsoft.com/config/debian/12/prod.list | tee /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy orchestrator requirements and install
COPY orchestrator_agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy orchestrator agent code, plus sql_agent (imported as a sibling package)
COPY orchestrator_agent/ .
COPY sql_agent/ ./sql_agent/

ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
