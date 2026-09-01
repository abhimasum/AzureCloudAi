# Local Testing Guide

This guide explains how to test the multi-agent system locally before deploying to GCP.

## Prerequisites

1. **Python 3.12+** installed
2. **GCP Authentication** configured:
   ```bash
   gcloud auth application-default login
   ```
3. **Virtual environments** for each agent (optional but recommended)

## Quick Start

### Option 1: Using the Test Script (Recommended)

```powershell
# Run the interactive testing script
.\test_local.ps1
```

The script will:
- Load environment variables from `.env.local`
- Verify GCP authentication
- Check/create BigQuery dataset
- Provide menu to test agents individually or together

### Option 2: Manual Testing

#### Step 1: Set Environment Variables

Copy `.env.local` and configure it:
```powershell
Copy-Item .env.local .env
# Edit .env with your values
```

Load environment variables:
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}
```

#### Step 2: Setup BigQuery (First Time Only)

```powershell
python infra/setup_bigquery.py
```

Verify tables:
```bash
bq ls geography_index
bq query "SELECT * FROM geography_index.countries"
```

#### Step 3: Test Individual Agents

**Retriever Agent** (RAG specialist):
```powershell
cd agents/retriever_agent
$env:PORT = "8081"
$env:RAG_CORPUS = "projects/1073291557100/locations/europe-west4/ragCorpora/576460752303423488"
python -m uvicorn a2a_app:a2a_app --host 0.0.0.0 --port 8081 --reload
```

Test: http://localhost:8081/.well-known/agent-card

**Orchestrator Agent** (with BigQuery):
```powershell
cd agents/orchestrator_agent
$env:PORT = "8080"
$env:RETRIEVER_AGENT_URL = "http://localhost:8081"  # Or deployed URL
python main.py
```

Test: http://localhost:8080 (Web UI)

## Testing Scenarios

### Test 1: BigQuery Agent (Metadata Search)

Visit http://localhost:8080 and ask:
```
What states are in India?
```

Expected flow:
1. Orchestrator delegates to BigQuery agent
2. BigQuery searches `states` table
3. Returns: Maharashtra, Karnataka, Tamil Nadu, Uttar Pradesh, West Bengal

### Test 2: RAG Agent (Document Search)

Ask:
```
Tell me about India's geography
```

Expected flow:
1. Orchestrator delegates to BigQuery (gets context)
2. Orchestrator delegates to Retriever (RAG search)
3. Returns combined answer with sources

### Test 3: Combined Flow (BigQuery → RAG)

Ask:
```
What is the capital of Maharashtra?
```

Expected flow:
1. BigQuery agent searches states: finds `{"id": 1, "name": "Maharashtra", "capital": "Mumbai"}`
2. Retriever agent searches RAG with BQ context
3. Combined answer: "The capital of Maharashtra is Mumbai" + additional details from documents

### Test 4: Greeting (No Delegation)

Ask:
```
Hello
```

Expected: Direct response without calling any agent

## Architecture Notes

### Agent Deployment Strategy

- **Retriever Agent**: Separate A2A service (independent scaling)
  - Deployed as separate Cloud Run service
  - Communicates via Agent-to-Agent protocol
  - Port 8081 locally

- **BigQuery Agent**: Local sub-agent (cost-efficient)
  - Runs inside orchestrator process
  - No separate deployment needed
  - Imported as Python module

- **Orchestrator Agent**: Main entry point
  - Includes BigQuery agent locally
  - Calls retriever via A2A
  - Port 8080 locally

### Environment Variables Required

| Variable | Used By | Description |
|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | All agents | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | Setup script | GCP region |
| `RAG_CORPUS` | Retriever | Full RAG corpus resource name |
| `RETRIEVER_AGENT_URL` | Orchestrator | URL to retriever A2A service |

## Deployment

After local testing succeeds:

```powershell
# Option 1: Using test script
.\test_local.ps1
# Select option 4

# Option 2: Manual push
git add -A
git commit -m "Your message"
git push origin master
```

Monitor deployment:
```bash
gh run watch
# Or visit: https://github.com/abhimasum/GoogleCloudAi/actions
```

Verify deployed services:
```bash
gcloud run services list --region=europe-west4
```

## Troubleshooting

### "Not authenticated with GCP"
```bash
gcloud auth application-default login
```

### "BigQuery dataset not found"
```bash
python infra/setup_bigquery.py
```

### "Connection refused to retriever"
- Ensure retriever agent is running on port 8081
- Or update `RETRIEVER_AGENT_URL` to deployed URL

### "Module not found: bigquery_agent"
- Ensure you're running from `agents/orchestrator_agent/` directory
- Check that `agents/bigquery_agent/` folder exists

## Next Steps

1. ✅ Test locally with this guide
2. ✅ Verify all three test scenarios work
3. ✅ Deploy via GitHub Actions
4. ✅ Test deployed version at Cloud Run URLs
5. 📝 Update sample data in BigQuery as needed
