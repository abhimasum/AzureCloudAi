FROM python:3.12-slim

WORKDIR /app

# Install build essentials for package compilation
RUN apt-get update && apt-get install -y build-essential python3-dev && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel --no-cache-dir

# Install dependencies
COPY requirements.txt .
RUN echo "Installing Python dependencies..." && \
    pip install --no-cache-dir -r requirements.txt --verbose 2>&1 | tail -50 && \
    echo "✓ Dependencies installed successfully" || \
    (echo "ERROR: Dependency installation failed" && exit 1)

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 900 main:app"]
