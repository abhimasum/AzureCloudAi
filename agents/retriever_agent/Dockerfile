FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# Cloud Run injects PORT; PUBLIC_URL must be set via --set-env-vars once the service URL is known.
CMD ["sh", "-c", "uvicorn a2a_app:a2a_app --host 0.0.0.0 --port ${PORT}"]
