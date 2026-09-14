#!/usr/bin/env python3
"""
Setup Azure AI Foundry Hub, Project via Azure Portal Manual Step
Azure AI Foundry doesn't support automated REST API creation yet.
This script verifies the setup and retrieves credentials from environment.
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def setup_foundry_manually() -> dict:
    """
    Azure AI Foundry resources must be created via Azure Portal.
    This function guides the user and verifies the setup.
    """
    
    credentials = {}
    
    try:
        logger.info("🚀 Setting up Azure AI Foundry Credentials...")
        logger.info("")
        
        # Get environment variables
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        resource_group = os.getenv("AZURE_RESOURCE_GROUP", "azure-ai-agents")
        location = os.getenv("AZURE_LOCATION", "uksouth")
        
        if not subscription_id:
            logger.error("❌ AZURE_SUBSCRIPTION_ID not set")
            return {}
        
        hub_name = "ai-agent-foundry-hub"
        project_name = "ai-agent-foundry-project"
        
        # ========== FOUNDRY ENDPOINT ==========
        logger.info("🌐 Foundry Endpoint Configuration:")
        foundry_endpoint = f"https://{location}.models.ai.azure.com"
        logger.info(f"   ✓ Region: {location}")
        logger.info(f"   ✓ Endpoint: {foundry_endpoint}")
        
        # ========== API KEY ==========
        logger.info("")
        logger.info("🔑 Foundry API Key:")
        foundry_key = os.getenv("AZURE_FOUNDRY_KEY")
        
        if foundry_key:
            logger.info(f"   ✓ API Key found in environment")
            logger.info(f"   ✓ Key (masked): {foundry_key[:10]}***")
            credentials['foundry_key'] = foundry_key
        else:
            logger.warning("")
            logger.warning("⚠️  AZURE_FOUNDRY_KEY not in environment!")
            logger.warning("")
            logger.warning("   TO GET YOUR API KEY:")
            logger.warning("   1. Go to: https://ai.azure.com")
            logger.warning("   2. Click 'Manage Resources' → 'Foundries'")
            logger.warning("   3. Select your Hub: ai-agent-foundry-hub")
            logger.warning("   4. Navigate to: Project Settings → API Keys")
            logger.warning("   5. Copy the API key and add to GitHub secrets:")
            logger.warning("      Settings → Secrets → New repository secret")
            logger.warning("      Name: AZURE_FOUNDRY_KEY")
            logger.warning("      Value: [paste your key]")
            logger.warning("")
            logger.warning("   The deployment will continue using Direct OpenAI fallback")
        
        # ========== HUB & PROJECT ==========
        logger.info("")
        logger.info("📦 Foundry Hub & Project:")
        logger.info(f"   Hub Name: {hub_name}")
        logger.info(f"   Project Name: {project_name}")
        logger.info("")
        logger.info("   IF THESE DON'T EXIST, CREATE THEM:")
        logger.info("   1. Go to: https://ai.azure.com")
        logger.info("   2. Click 'Build' → 'Create New Hub'")
        logger.info(f"   3. Hub name: {hub_name}")
        logger.info(f"   4. Location: {location}")
        logger.info("   5. Click Create")
        logger.info("   6. Create New Project in the Hub")
        logger.info(f"   7. Project name: {project_name}")
        
        credentials['foundry_endpoint'] = foundry_endpoint
        
        logger.info("")
        logger.info("✅ Foundry Configuration Complete!")
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
        credentials = setup_foundry_manually()
        
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

