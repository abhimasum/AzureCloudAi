# Local Testing Script for Multi-Agent System
# Run this script to test agents locally before deploying

Write-Host "=== Local Agent Testing Script ===" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (Test-Path .venv\Scripts\Activate.ps1) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & .\.venv\Scripts\Activate.ps1
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "Then run: .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Load environment variables from .env.local
if (Test-Path .env.local) {
    Write-Host "Loading environment variables from .env.local..." -ForegroundColor Green
    Get-Content .env.local | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "  $name set" -ForegroundColor Gray
        }
    }
    Write-Host ""
} else {
    Write-Host "ERROR: .env.local file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.local to .env and configure it first." -ForegroundColor Yellow
    exit 1
}

# Check if user is authenticated with GCP
Write-Host "Checking GCP authentication..." -ForegroundColor Yellow
$authCheck = gcloud auth application-default print-access-token 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not authenticated with GCP!" -ForegroundColor Red
    Write-Host "Run: gcloud auth application-default login" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ GCP authentication verified" -ForegroundColor Green
Write-Host ""

# Check if BigQuery dataset exists
Write-Host "Verifying BigQuery dataset..." -ForegroundColor Yellow
$bqCheck = bq ls geography_index 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: BigQuery dataset 'geography_index' not found!" -ForegroundColor Yellow
    Write-Host "Creating BigQuery dataset and tables..." -ForegroundColor Cyan
    python infra/setup_bigquery.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to setup BigQuery!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ BigQuery dataset verified" -ForegroundColor Green
Write-Host ""

# Show menu
Write-Host "Select testing mode:" -ForegroundColor Cyan
Write-Host "1. Test Retriever Agent only (port 8081)"
Write-Host "2. Test Orchestrator Agent only (port 8080) - requires retriever deployed or running"
Write-Host "3. Test Both Agents (retriever on 8081, orchestrator on 8080)"
Write-Host "4. Deploy to GCP via GitHub Actions"
Write-Host ""
$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "=== Starting Retriever Agent ===" -ForegroundColor Cyan
        Write-Host "Port: 8081" -ForegroundColor Gray
        Write-Host "Test URL: http://localhost:8081/.well-known/agent-card" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host ""
        
        Set-Location agents/retriever_agent
        $env:PORT = "8081"
        python -m uvicorn a2a_app:a2a_app --host 0.0.0.0 --port 8081 --reload
    }
    
    "2" {
        Write-Host ""
        Write-Host "=== Starting Orchestrator Agent ===" -ForegroundColor Cyan
        Write-Host "Port: 8080" -ForegroundColor Gray
        Write-Host "Web UI: http://localhost:8080" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Note: Ensure retriever is running (locally on 8081 or deployed)" -ForegroundColor Yellow
        Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
        Write-Host ""
        
        Set-Location agents/orchestrator_agent
        $env:PORT = "8080"
        python main.py
    }
    
    "3" {
        Write-Host ""
        Write-Host "=== Starting Both Agents ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Starting retriever agent in background (port 8081)..." -ForegroundColor Yellow
        
        # Start retriever in background
        $retrieverJob = Start-Job -ScriptBlock {
            param($projectRoot)
            Set-Location "$projectRoot/agents/retriever_agent"
            $env:GOOGLE_CLOUD_PROJECT = $using:env:GOOGLE_CLOUD_PROJECT
            $env:RAG_CORPUS = $using:env:RAG_CORPUS
            $env:PORT = "8081"
            python -m uvicorn a2a_app:a2a_app --host 0.0.0.0 --port 8081
        } -ArgumentList (Get-Location).Path
        
        # Wait for retriever to start
        Write-Host "Waiting for retriever to start..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        
        # Test retriever
        try {
            $testUrl = "http://localhost:8081/.well-known/agent-card"
            $response = Invoke-WebRequest -Uri $testUrl -UseBasicParsing -TimeoutSec 5
            Write-Host "✓ Retriever agent started successfully" -ForegroundColor Green
        } catch {
            Write-Host "WARNING: Retriever agent may not be ready yet" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "Starting orchestrator agent (port 8080)..." -ForegroundColor Yellow
        Write-Host "Web UI: http://localhost:8080" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Press Ctrl+C to stop (will also stop retriever)" -ForegroundColor Yellow
        Write-Host ""
        
        try {
            Set-Location agents/orchestrator_agent
            $env:PORT = "8080"
            $env:RETRIEVER_AGENT_URL = "http://localhost:8081"
            python main.py
        } finally {
            Write-Host ""
            Write-Host "Stopping retriever agent..." -ForegroundColor Yellow
            Stop-Job $retrieverJob
            Remove-Job $retrieverJob
            Write-Host "✓ Both agents stopped" -ForegroundColor Green
        }
    }
    
    "4" {
        Write-Host ""
        Write-Host "=== Deploying to GCP ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "This will trigger the GitHub Actions workflow to deploy all services." -ForegroundColor Yellow
        Write-Host ""
        
        # Check if there are uncommitted changes
        $status = git status --porcelain
        if ($status) {
            Write-Host "WARNING: You have uncommitted changes:" -ForegroundColor Yellow
            git status --short
            Write-Host ""
            $commit = Read-Host "Commit and push changes? (y/n)"
            if ($commit -eq "y") {
                $message = Read-Host "Commit message"
                git add -A
                git commit -m $message
                git push origin master
                Write-Host "✓ Changes pushed" -ForegroundColor Green
            } else {
                Write-Host "Deployment cancelled" -ForegroundColor Yellow
                exit 0
            }
        } else {
            Write-Host "No uncommitted changes. Triggering workflow..." -ForegroundColor Green
            git push origin master
        }
        
        Write-Host ""
        Write-Host "✓ Deployment triggered!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Monitor deployment at:" -ForegroundColor Cyan
        Write-Host "https://github.com/abhimasum/GoogleCloudAi/actions" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Or run: gh run watch" -ForegroundColor Gray
    }
    
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}
