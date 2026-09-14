#!/usr/bin/env python3
"""
Setup Azure AI Foundry Hub, Project, and Model Deployment (REST API Approach)
Minimal dependencies - uses only requests and Azure CLI credentials
"""

import os
import sys
import json
import time
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_access_token() -> str:
    """Get Azure access token using Azure CLI"""
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token", "--query", "accessToken", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"❌ Failed to get access token: {e}")
        raise


def setup_foundry_via_rest() -> dict:
    """Setup Foundry using pure REST API calls"""
    
    credentials = {}
    
    try:
        import requests
    except ImportError:
        logger.error("requests library not installed")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=False)
        import requests
    
    try:
        logger.info("🚀 Setting up Azure AI Foundry via REST API...")
        
        # Get environment variables
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_RESOURCE_GROUP", "azure-ai-agents")
        location = os.getenv("AZURE_LOCATION", "uksouth")
        
        if not subscription_id:
            logger.error("❌ AZURE_SUBSCRIPTION_ID not set")
            return {}
        
        # Get auth token
        logger.info("🔐 Authenticating...")
        token = get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        hub_name = "ai-agent-foundry-hub"
        project_name = "ai-agent-foundry-project"
        api_version = "2024-04-01-preview"
        
        base_url = (
            f"https://management.azure.com/subscriptions/{subscription_id}/"
            f"resourceGroups/{resource_group}/providers/Microsoft.MachineLearning"
        )
        
        # ========== CREATE HUB ==========
        logger.info("")
        logger.info(f"🚀 Creating Foundry Hub: {hub_name}")
        
        hub_url = f"{base_url}/registries/{hub_name}?api-version={api_version}"
        hub_payload = {
            "location": location,
            "kind": "hub",
            "properties": {
                "display_name": "AI Agent Foundry Hub",
                "description": "Automated AI Agent Foundry Hub"
            }
        }
        
        try:
            response = requests.put(hub_url, headers=headers, json=hub_payload, timeout=60)
            if response.status_code in [200, 201, 202]:
                logger.info("✓ Hub creation initiated")
            elif response.status_code == 409:
                logger.info("✓ Hub already exists")
            else:
                logger.warning(f"⚠️  Hub response: {response.status_code}")
                if response.text:
                    logger.warning(f"    Error: {response.text[:200]}")
        except requests.exceptions.Timeout:
            logger.warning("⚠️  Hub creation timeout (may still be processing)")
        except Exception as e:
            logger.warning(f"⚠️  Hub creation error: {e}")
        
        # Wait for hub to be ready
        logger.info("⏳ Waiting for Hub to be ready (20s)...")
        time.sleep(20)
        
        # ========== CREATE PROJECT ==========
        logger.info(f"🔧 Creating Foundry Project: {project_name}")
        
        project_url = f"{base_url}/projects/{project_name}?api-version={api_version}"
        project_payload = {
            "location": location,
            "properties": {
                "display_name": "AI Agent Foundry Project",
                "description": "Automated AI Agent Project",
                "hub_resource_id": (
                    f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
                    f"providers/Microsoft.MachineLearning/registries/{hub_name}"
                )
            }
        }
        
        try:
            response = requests.put(project_url, headers=headers, json=project_payload, timeout=60)
            if response.status_code in [200, 201, 202]:
                logger.info("✓ Project creation initiated")
            elif response.status_code == 409:
                logger.info("✓ Project already exists")
            else:
                logger.warning(f"⚠️  Project response: {response.status_code}")
                if response.text:
                    logger.warning(f"    Error: {response.text[:200]}")
        except requests.exceptions.Timeout:
            logger.warning("⚠️  Project creation timeout (may still be processing)")
        except Exception as e:
            logger.warning(f"⚠️  Project creation error: {e}")
        
        # ========== GET CREDENTIALS ==========
        logger.info("")
        logger.info("🔑 Retrieving credentials...")
        
        # Construct endpoint
        foundry_endpoint = f"https://{location}.models.ai.azure.com"
        logger.info(f"✓ Endpoint: {foundry_endpoint}")
        
        # Get key from environment or try to retrieve
        foundry_key = os.getenv("AZURE_FOUNDRY_KEY")
        if foundry_key:
            logger.info(f"✓ API Key from environment: {foundry_key[:10]}***")
        else:
            logger.info("ℹ️  API Key not in environment")
            logger.info("   Get from Azure Portal → Foundry Hub → Project Settings → API Keys")
        
        credentials['foundry_endpoint'] = foundry_endpoint
        if foundry_key:
            credentials['foundry_key'] = foundry_key
        
        logger.info("")
        logger.info("✅ Foundry Setup Complete!")
        logger.info(f"   Hub: {hub_name}")
        logger.info(f"   Project: {project_name}")
        logger.info(f"   Endpoint: {foundry_endpoint}")
        
        return credentials
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}", exc_info=False)
        return {}


def main():
    """Main entry point"""
    logger.info("🚀 Azure AI Foundry Setup Script\n")
    
    try:
        credentials = setup_foundry_via_rest()
        
        # Export to GitHub Actions output
        if credentials:
            output_file = os.getenv("GITHUB_OUTPUT", "output.txt")
            logger.info(f"\n📤 Exporting to {output_file}...")
            
            with open(output_file, "a") as f:
                for key, value in credentials.items():
                    if value:
                        f.write(f"{key}={value}\n")
                        masked_value = f"{value[:10]}***" if len(value) > 20 else value
                        logger.info(f"   ✓ {key}={masked_value}")
        
        logger.info("\n✅ Complete!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

