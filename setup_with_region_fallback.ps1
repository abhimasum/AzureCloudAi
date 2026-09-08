# Azure Infrastructure Setup with Region Fallback
# Automatically tries alternative regions if provisioning fails
# Usage: .\setup_with_region_fallback.ps1

Write-Host "=== Azure Setup with Region Fallback ===" -ForegroundColor Cyan
Write-Host ""

# List of regions to try (in order of preference)
$regions = @(
    "northeurope",      # North Europe (primary)
    "westeurope",       # West Europe
    "uksouth",         # UK South
    "centralindia",    # Central India
    "southindia",      # South India
    "eastus",          # East US
    "eastus2",         # East US 2
    "westus",          # West US
    "canadacentral"    # Canada Central
)

# Check if user is logged in
Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
$accountCheck = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not logged in to Azure!" -ForegroundColor Red
    Write-Host "Run: az login" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Azure authentication verified" -ForegroundColor Green
Write-Host ""

# Get configuration
Write-Host "=== Configuration ===" -ForegroundColor Yellow
$resourceGroup = Read-Host "Resource Group name [azure-ai-agents]"
if ([string]::IsNullOrWhiteSpace($resourceGroup)) { $resourceGroup = "azure-ai-agents" }

$sqlServerName = Read-Host "SQL Server name [ai-agents-sql-$(Get-Random)]"
if ([string]::IsNullOrWhiteSpace($sqlServerName)) { $sqlServerName = "ai-agents-sql-$(Get-Random)" }

$sqlAdminUser = Read-Host "SQL Admin username [sqladmin]"
if ([string]::IsNullOrWhiteSpace($sqlAdminUser)) { $sqlAdminUser = "sqladmin" }

$sqlAdminPassword = Read-Host "SQL Admin password (min 12 chars, complex)" -AsSecureString
$sqlAdminPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUni($sqlAdminPassword))

if ($sqlAdminPasswordPlain.Length -lt 12) {
    Write-Host "ERROR: Password must be at least 12 characters" -ForegroundColor Red
    exit 1
}

$openaiName = Read-Host "Azure OpenAI resource name [ai-agents-openai]"
if ([string]::IsNullOrWhiteSpace($openaiName)) { $openaiName = "ai-agents-openai" }

$searchName = Read-Host "AI Search service name [ai-agents-search]"
if ([string]::IsNullOrWhiteSpace($searchName)) { $searchName = "ai-agents-search" }

$storageName = Read-Host "Storage account name [aiagentsstorage$(Get-Random)]"
if ([string]::IsNullOrWhiteSpace($storageName)) { $storageName = "aiagentsstorage$(Get-Random)" }

$acrName = Read-Host "Container Registry name [aiagentsacr]"
if ([string]::IsNullOrWhiteSpace($acrName)) { $acrName = "aiagentsacr" }

$containerEnv = Read-Host "Container Apps Environment [ai-agents-env]"
if ([string]::IsNullOrWhiteSpace($containerEnv)) { $containerEnv = "ai-agents-env" }

Write-Host ""
Write-Host "=== Starting Setup with Region Fallback ===" -ForegroundColor Cyan
Write-Host "Trying regions in order: $($regions -join ', ')" -ForegroundColor Gray
Write-Host ""

$successfulRegion = $null
$lastError = $null

foreach ($region in $regions) {
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host "Attempting provisioning in: $region" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host ""

    try {
        # Create Resource Group
        Write-Host "📦 Creating/Verifying Resource Group: $resourceGroup" -ForegroundColor Yellow
        $rgExists = az group exists --name $resourceGroup | ConvertFrom-Json
        
        if ($rgExists -eq $false) {
            Write-Host "  Creating new Resource Group in $region..." -ForegroundColor Cyan
            az group create `
                --name $resourceGroup `
                --location $region | Out-Null
            
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create resource group in $region"
            }
            Write-Host "  ✓ Resource Group created" -ForegroundColor Green
        } else {
            Write-Host "  ✓ Resource Group already exists" -ForegroundColor Green
        }
        Write-Host ""

        # Register providers
        Write-Host "📋 Registering resource providers..." -ForegroundColor Yellow
        $providers = @(
            "Microsoft.Sql",
            "Microsoft.CognitiveServices",
            "Microsoft.Search",
            "Microsoft.Storage",
            "Microsoft.ContainerRegistry",
            "Microsoft.App",
            "Microsoft.OperationalInsights"
        )
        
        foreach ($provider in $providers) {
            Write-Host "  Registering $provider..." -ForegroundColor Gray
            az provider register --namespace $provider --accept-terms 2>&1 | Out-Null
        }
        Write-Host "  ✓ Waiting 120 seconds for provider registration..." -ForegroundColor Gray
        Start-Sleep -Seconds 120
        Write-Host "  ✓ Providers registered" -ForegroundColor Green
        Write-Host ""

        # Try to create SQL Server (most likely to fail with region error)
        Write-Host "🗄️ Creating SQL Server: $sqlServerName" -ForegroundColor Yellow
        
        $sqlExists = az sql server show --name $sqlServerName --resource-group $resourceGroup 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ SQL Server already exists" -ForegroundColor Green
        } else {
            Write-Host "  Creating SQL Server in $region..." -ForegroundColor Cyan
            
            $sqlOutput = az sql server create `
                --name $sqlServerName `
                --resource-group $resourceGroup `
                --location $region `
                --admin-user $sqlAdminUser `
                --admin-password $sqlAdminPasswordPlain `
                --enable-public-network true 2>&1
            
            # Check for region error
            if ($LASTEXITCODE -ne 0) {
                $errorMsg = $sqlOutput -join " "
                if ($errorMsg -like "*RegionDoesNotAllowProvisioning*") {
                    Write-Host "  ⚠️ Region '$region' is not accepting SQL Server creation" -ForegroundColor Yellow
                    Write-Host "     Trying next region..." -ForegroundColor Yellow
                    Write-Host ""
                    continue
                } else {
                    throw "SQL Server creation failed: $errorMsg"
                }
            }
            Write-Host "  ✓ SQL Server created" -ForegroundColor Green
        }
        Write-Host ""

        # Create database
        Write-Host "📊 Creating SQL Database..." -ForegroundColor Yellow
        $dbExists = az sql db show --name geography_index --server $sqlServerName --resource-group $resourceGroup 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Database already exists" -ForegroundColor Green
        } else {
            az sql db create `
                --name geography_index `
                --server $sqlServerName `
                --resource-group $resourceGroup `
                --service-objective S0 2>&1 | Out-Null
            
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create SQL database"
            }
            Write-Host "  ✓ Database created" -ForegroundColor Green
        }
        Write-Host ""

        # Add firewall rule
        Write-Host "🔒 Configuring SQL firewall..." -ForegroundColor Yellow
        az sql server firewall-rule create `
            --resource-group $resourceGroup `
            --server $sqlServerName `
            --name AllowAzureServices `
            --start-ip-address 0.0.0.0 `
            --end-ip-address 0.0.0.0 2>&1 | Out-Null
        Write-Host "  ✓ Firewall rule created" -ForegroundColor Green
        Write-Host ""

        # If we got here, provisioning succeeded
        $successfulRegion = $region
        Write-Host "✅ SQL Server provisioning succeeded in $region!" -ForegroundColor Green
        break

    } catch {
        $lastError = $_.Exception.Message
        Write-Host "❌ Error in $region : $lastError" -ForegroundColor Red
        Write-Host "   Trying next region..." -ForegroundColor Yellow
        Write-Host ""
        continue
    }
}

if ($null -eq $successfulRegion) {
    Write-Host ""
    Write-Host "❌ PROVISIONING FAILED" -ForegroundColor Red
    Write-Host "All regions exhausted. Last error: $lastError" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "1. Check your Azure quota limits" -ForegroundColor Gray
    Write-Host "2. Verify your subscription type (free tier may be limited)" -ForegroundColor Gray
    Write-Host "3. Try a different subscription if available" -ForegroundColor Gray
    Write-Host "4. Contact Azure support if regions are consistently unavailable" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ PROVISIONING SUCCESSFUL" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration Summary:" -ForegroundColor Cyan
Write-Host "  Resource Group: $resourceGroup" -ForegroundColor Gray
Write-Host "  Region: $successfulRegion" -ForegroundColor Gray
Write-Host "  SQL Server: $sqlServerName" -ForegroundColor Gray
Write-Host "  SQL Database: geography_index" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update .env file with your connection strings" -ForegroundColor Gray
Write-Host "2. Run: python infra/setup_azure_sql.py" -ForegroundColor Gray
Write-Host "3. Run: .\test_local.ps1" -ForegroundColor Gray
Write-Host ""

# Save region to file for reference
Write-Host "Saving region configuration..." -ForegroundColor Yellow
$configFile = "deployment-region.txt"
@"
Successful Deployment Region: $successfulRegion
Date: $(Get-Date)
Resource Group: $resourceGroup
"@ | Out-File -FilePath $configFile -Encoding UTF8
Write-Host "✓ Configuration saved to $configFile" -ForegroundColor Green
