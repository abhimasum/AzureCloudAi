#!/bin/bash
# Azure Infrastructure Setup Script
# Sets up all required Azure resources for the multi-agent system
# Usage: ./setup_azure.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Azure Multi-Agent System Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if user is logged in
if ! az account show &>/dev/null; then
    echo -e "${RED}✗ Not logged into Azure CLI${NC}"
    echo "Run: az login"
    exit 1
fi

# Get current subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Logged in to Azure${NC}"
echo "  Subscription: $SUBSCRIPTION_NAME"
echo "  ID: $SUBSCRIPTION_ID"

# Configuration
echo ""
echo -e "${YELLOW}=== Configuration ===${NC}"
read -p "Resource Group name [azure-ai-agents]: " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-azure-ai-agents}

read -p "Location [eastus]: " LOCATION
LOCATION=${LOCATION:-eastus}

read -p "SQL Server name [ai-agents-sql-$(date +%s)]: " SQL_SERVER
SQL_SERVER=${SQL_SERVER:-ai-agents-sql-$(date +%s)}

read -p "SQL Admin username [sqladmin]: " SQL_ADMIN_USER
SQL_ADMIN_USER=${SQL_ADMIN_USER:-sqladmin}

read -sp "SQL Admin password (min 12 chars, complex): " SQL_ADMIN_PASSWORD
echo ""

if [ ${#SQL_ADMIN_PASSWORD} -lt 12 ]; then
    echo -e "${RED}✗ Password must be at least 12 characters${NC}"
    exit 1
fi

read -p "Azure OpenAI resource name [ai-agents-openai]: " OPENAI_NAME
OPENAI_NAME=${OPENAI_NAME:-ai-agents-openai}

read -p "AI Search service name [ai-agents-search]: " SEARCH_NAME
SEARCH_NAME=${SEARCH_NAME:-ai-agents-search}

read -p "Storage account name [aiagentsstorage$(date +%s)]: " STORAGE_NAME
STORAGE_NAME=${STORAGE_NAME:-aiagentsstorage$(date +%s)}

read -p "Container Registry name [aiagentsacr]: " ACR_NAME
ACR_NAME=${ACR_NAME:-aiagentsacr}

read -p "Container Apps Environment [ai-agents-env]: " CONTAINER_ENV
CONTAINER_ENV=${CONTAINER_ENV:-ai-agents-env}

echo ""
echo -e "${YELLOW}=== Summary ===${NC}"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "SQL Server: $SQL_SERVER"
echo "Azure OpenAI: $OPENAI_NAME"
echo "AI Search: $SEARCH_NAME"
echo "Storage: $STORAGE_NAME"
echo "ACR: $ACR_NAME"
echo ""
read -p "Proceed with setup? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

# Create Resource Group
echo ""
echo -e "${YELLOW}[1/9] Creating Resource Group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION
echo -e "${GREEN}✓ Resource group created${NC}"

# Create Azure SQL Server and Database
echo ""
echo -e "${YELLOW}[2/9] Creating Azure SQL Server...${NC}"
az sql server create \
  --name $SQL_SERVER \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --admin-user $SQL_ADMIN_USER \
  --admin-password "$SQL_ADMIN_PASSWORD"

# Allow Azure services to access SQL Server
az sql server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Create database
az sql db create \
  --resource-group $RESOURCE_GROUP \
  --server $SQL_SERVER \
  --name geography_index \
  --edition Basic \
  --compute-model Serverless \
  --family Gen5 \
  --capacity 1

echo -e "${GREEN}✓ Azure SQL Server created${NC}"

# Create Azure OpenAI
echo ""
echo -e "${YELLOW}[3/9] Creating Azure OpenAI...${NC}"
az cognitiveservices account create \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

echo -e "${GREEN}✓ Azure OpenAI created with GPT-4o deployment${NC}"

# Create AI Search
echo ""
echo -e "${YELLOW}[4/9] Creating Azure AI Search...${NC}"
az search service create \
  --name $SEARCH_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Basic

echo -e "${GREEN}✓ Azure AI Search created${NC}"

# Create Storage Account and Container
echo ""
echo -e "${YELLOW}[5/9] Creating Storage Account...${NC}"
az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Get storage connection string
STORAGE_CONN=$(az storage account show-connection-string \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

# Create blob container
az storage container create \
  --name documents \
  --connection-string "$STORAGE_CONN"

echo -e "${GREEN}✓ Storage account created${NC}"

# Create Container Registry
echo ""
echo -e "${YELLOW}[6/9] Creating Azure Container Registry...${NC}"
az acr create \
  --name $ACR_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Basic \
  --admin-enabled true

echo -e "${GREEN}✓ Container Registry created${NC}"

# Create Container Apps Environment
echo ""
echo -e "${YELLOW}[7/9] Creating Container Apps Environment...${NC}"
az containerapp env create \
  --name $CONTAINER_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

echo -e "${GREEN}✓ Container Apps environment created${NC}"

# Setup SQL Database Schema
echo ""
echo -e "${YELLOW}[8/9] Setting up SQL Database schema...${NC}"

# Export variables for Python script
export AZURE_SQL_SERVER="${SQL_SERVER}.database.windows.net"
export AZURE_SQL_DATABASE="geography_index"
export AZURE_SQL_USERNAME="$SQL_ADMIN_USER"
export AZURE_SQL_PASSWORD="$SQL_ADMIN_PASSWORD"

python3 infra/setup_azure_sql.py

echo -e "${GREEN}✓ SQL Database schema created${NC}"

# Create AI Search Index
echo ""
echo -e "${YELLOW}[9/9] Creating AI Search index...${NC}"

SEARCH_KEY=$(az search admin-key show \
  --resource-group $RESOURCE_GROUP \
  --service-name $SEARCH_NAME \
  --query primaryKey -o tsv)

# Create index using REST API
curl -X PUT "https://${SEARCH_NAME}.search.windows.net/indexes/documents?api-version=2023-11-01" \
  -H "Content-Type: application/json" \
  -H "api-key: $SEARCH_KEY" \
  -d '{
    "name": "documents",
    "fields": [
      {"name": "id", "type": "Edm.String", "key": true, "searchable": false},
      {"name": "content", "type": "Edm.String", "searchable": true},
      {"name": "title", "type": "Edm.String", "searchable": true, "filterable": true},
      {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": true, "dimensions": 1536, "vectorSearchProfile": "default-vector-profile"}
    ],
    "vectorSearch": {
      "profiles": [
        {
          "name": "default-vector-profile",
          "algorithm": "default-algorithm"
        }
      ],
      "algorithms": [
        {
          "name": "default-algorithm",
          "kind": "hnsw"
        }
      ]
    }
  }'

echo -e "${GREEN}✓ AI Search index created${NC}"

# Get all credentials
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Save these credentials (add to .env file):${NC}"
echo ""
echo "# Azure SQL"
echo "AZURE_SQL_SERVER=${SQL_SERVER}.database.windows.net"
echo "AZURE_SQL_DATABASE=geography_index"
echo "AZURE_SQL_USERNAME=$SQL_ADMIN_USER"
echo "AZURE_SQL_PASSWORD=$SQL_ADMIN_PASSWORD"
echo ""
echo "# Azure OpenAI"
OPENAI_ENDPOINT=$(az cognitiveservices account show --name $OPENAI_NAME --resource-group $RESOURCE_GROUP --query properties.endpoint -o tsv)
OPENAI_KEY=$(az cognitiveservices account keys list --name $OPENAI_NAME --resource-group $RESOURCE_GROUP --query key1 -o tsv)
echo "AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT"
echo "AZURE_OPENAI_API_KEY=$OPENAI_KEY"
echo "AZURE_OPENAI_DEPLOYMENT=gpt-4o"
echo ""
echo "# Azure AI Search"
echo "AZURE_SEARCH_ENDPOINT=https://${SEARCH_NAME}.search.windows.net"
echo "AZURE_SEARCH_KEY=$SEARCH_KEY"
echo "AZURE_SEARCH_INDEX=documents"
echo ""
echo "# Storage"
echo "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN"
echo "AZURE_STORAGE_CONTAINER=documents"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy credentials above to .env file"
echo "2. Run: pip install -r requirements.txt"
echo "3. Test locally: python agents/orchestrator_agent/main.py"
echo "4. Setup GitHub secrets for CI/CD"
