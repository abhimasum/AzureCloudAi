# Script to run document ingestion into Azure AI Search

Write-Host "=== Document Ingestion Script ===" -ForegroundColor Green

# Check required environment variables
Write-Host "`nChecking required environment variables..." -ForegroundColor Yellow

$requiredVars = @{
    "AZURE_SEARCH_ENDPOINT" = "Azure AI Search endpoint"
    "AZURE_SEARCH_KEY" = "Azure AI Search API key"
    "OPENAI_API_KEY" = "OpenAI API key (for embeddings)"
}

$allVarsSet = $true
foreach ($var in $requiredVars.GetEnumerator()) {
    $value = [Environment]::GetEnvironmentVariable($var.Name)
    if ($value) {
        $masked = $value.Substring(0, [Math]::Min(10, $value.Length)) + "***"
        Write-Host "✓ $($var.Name): $masked" -ForegroundColor Green
    } else {
        Write-Host "✗ $($var.Name): NOT SET - $($var.Value)" -ForegroundColor Red
        $allVarsSet = $false
    }
}

if (-not $allVarsSet) {
    Write-Host "`n❌ Missing required environment variables!" -ForegroundColor Red
    Write-Host "Please set all required variables and try again." -ForegroundColor Yellow
    exit 1
}

# Check optional variables
Write-Host "`nChecking optional environment variables..." -ForegroundColor Yellow
$optionalVars = @("AZURE_SEARCH_INDEX", "AZURE_OPENAI_ENDPOINT")
foreach ($var in $optionalVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        Write-Host "✓ $var (set)" -ForegroundColor Cyan
    } else {
        Write-Host "  $var (not set - using defaults)" -ForegroundColor Gray
    }
}

# Run ingestion
Write-Host "`n=== Running Ingestion ===" -ForegroundColor Green
cd ingestion
python ingest.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Ingestion completed successfully!" -ForegroundColor Green
    Write-Host "Documents should now be searchable in Azure AI Search." -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Ingestion failed with exit code: $LASTEXITCODE" -ForegroundColor Red
}
