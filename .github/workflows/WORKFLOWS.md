# GitHub Actions Workflows - OpenAI vs Foundry

This folder contains two separate deployment strategies:

## 📂 Folder Structure

```
.github/workflows/
├── OpenAi/
│   ├── deploy.yml              # Direct OpenAI deployment (default)
│   └── cleanup-full.yml        # OpenAI cleanup workflow
├── Foundry/
│   ├── deploy.yml              # Azure Foundry deployment
│   └── cleanup-full.yml        # Foundry cleanup workflow
└── WORKFLOWS.md                # This file
```

## 🚀 How to Use Each Workflow

### Option 1: Direct OpenAI (Current Default)
**Best for:** Development, testing, cost-conscious usage

**Configuration:**
- Uses `OPENAI_API_KEY` secret
- No additional Azure Foundry setup needed
- `USE_AZURE_FOUNDRY: false`
- `MODEL_NAME: gpt-4o`

**To use:**
1. No changes needed - this is the default configuration
2. Code changes will NOT trigger from Foundry/deploy.yml
3. Only OpenAi/deploy.yml will respond to agents/** changes

**Workflow triggers:**
- Push to master with changes in `agents/`, `ingestion/`, `infra/`
- Manual trigger via GitHub Actions → OpenAI → Run workflow

### Option 2: Azure Foundry (Multi-Model)
**Best for:** Production, cost optimization, multi-model support

**Configuration:**
- Uses Azure Foundry credentials (AZURE_FOUNDRY_ENDPOINT, AZURE_FOUNDRY_KEY)
- Requires Azure Foundry Hub setup
- `USE_AZURE_FOUNDRY: true`
- `MODEL_NAME: gpt-4o` (or claude-3-5-sonnet)

**To use:**
1. Set up Azure AI Foundry:
   - Create Hub in Azure Portal
   - Deploy models (gpt-4o minimum)
   - Get endpoint and API key
   
2. Add GitHub secrets:
   - `AZURE_FOUNDRY_ENDPOINT`: https://your-hub.models.ai.azure.com
   - `AZURE_FOUNDRY_KEY`: [API key from Foundry]
   
3. Trigger deployment:
   - Push code changes will NOT trigger Foundry workflow (different paths)
   - Use GitHub Actions → Foundry → Run workflow (manual)
   - Or rename `Foundry/deploy.yml` to root to make it auto-trigger

**Workflow triggers:**
- Manual trigger via GitHub Actions → Foundry → Run workflow
- Or push changes to `.github/workflows/Foundry/deploy.yml`

## 🔄 How to Switch Between Them

### Automatic Triggering (Push-based)

If you want code pushes to automatically trigger Foundry instead of OpenAI:

```bash
# Copy Foundry workflow to root
cp .github/workflows/Foundry/deploy.yml .github/workflows/deploy.yml
cp .github/workflows/Foundry/cleanup-full.yml .github/workflows/cleanup-full.yml

# Commit
git add .github/workflows/deploy.yml .github/workflows/cleanup-full.yml
git commit -m "Switch to Foundry deployment (auto-trigger on push)"
git push origin master
```

To switch back to OpenAI:

```bash
# Copy OpenAI workflow to root
cp .github/workflows/OpenAi/deploy.yml .github/workflows/deploy.yml
cp .github/workflows/OpenAi/cleanup-full.yml .github/workflows/cleanup-full.yml

# Commit
git add .github/workflows/deploy.yml .github/workflows/cleanup-full.yml
git commit -m "Switch to Direct OpenAI deployment (auto-trigger on push)"
git push origin master
```

### Manual Triggering

No need to copy files - just use GitHub Actions UI:
- Go to Actions tab
- Select "Deploy Azure MAF Agents using Foundry" or "Deploy Azure MAF Agents using Open AI"
- Click "Run workflow"

## 📋 Environment Variables Comparison

| Variable | OpenAI | Foundry |
|----------|--------|---------|
| `USE_AZURE_FOUNDRY` | `false` | `true` |
| `MODEL_NAME` | `gpt-4o` | `gpt-4o` or `claude-3-5-sonnet` |
| `AZURE_FOUNDRY_ENDPOINT` | Not used | From secrets |
| `AZURE_FOUNDRY_KEY` | Not used | From secrets |
| Required Secrets | `OPENAI_API_KEY` | `AZURE_FOUNDRY_ENDPOINT`<br/>`AZURE_FOUNDRY_KEY` |

## ✅ Validation Checklist

### For OpenAI Workflow:
- [ ] `OPENAI_API_KEY` secret is set in GitHub
- [ ] `MODEL_NAME: gpt-4o` in env
- [ ] `USE_AZURE_FOUNDRY: false` in env
- [ ] Trigger path: `.github/workflows/OpenAi/deploy.yml`

### For Foundry Workflow:
- [ ] `AZURE_FOUNDRY_ENDPOINT` secret is set in GitHub
- [ ] `AZURE_FOUNDRY_KEY` secret is set in GitHub
- [ ] `MODEL_NAME: gpt-4o` in env
- [ ] `USE_AZURE_FOUNDRY: true` in env
- [ ] Azure Foundry Hub exists with models deployed
- [ ] Trigger path: `.github/workflows/Foundry/deploy.yml`

## 🎯 Recommended Setup

1. **Initial setup**: Use OpenAI folder (already configured)
2. **Test Foundry**: Use manual trigger from GitHub Actions UI
3. **Production switch**: Copy Foundry files to root when ready
4. **Fallback**: Keep OpenAI files in subfolder for quick rollback

## 📚 References

- [FOUNDRY_SETUP.md](../FOUNDRY_SETUP.md) - Detailed Foundry setup guide
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
