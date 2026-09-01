# Azure Cloud AI Multi-Agent System

Multi-agent Q&A system for Indian geography using **Microsoft Agent Framework (MAF)**, **Azure OpenAI**, **Azure SQL**, and **Azure AI Search**.

## Architecture

| Service | Role in this project |
|---|---|
| **Microsoft Agent Framework** | Builds all agents with graph-based workflows |
| **Azure OpenAI (GPT-4o)** | The LLM that powers each agent |
| **Azure AI Search** | Vector search and RAG for document retrieval |
| **Azure Blob Storage** | Holds source documents for ingestion |
| **Azure SQL Database** | Stores geography index (countries, states, districts) |
| **A2A protocol** | Agent-to-agent communication between services |
| **Azure Container Apps** | Hosts all agents and ingestion service |
| **Azure Container Registry** | Stores Docker images |
| **GitHub Actions** | CI/CD pipeline |

## Quick Start

See [docs/SETUP.md](docs/SETUP.md) for full setup instructions.
