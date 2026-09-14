# ⚠️ IMPORTANT: GitHub Actions Workflow Discovery

## The Issue

GitHub Actions **ONLY** discovers workflow files directly in `.github/workflows/` root directory.

Workflows in subdirectories like:
- `.github/workflows/Foundry/deploy.yml` ❌ NOT discovered
- `.github/workflows/OpenAi/deploy.yml` ❌ NOT discovered

Will NOT appear in the GitHub Actions UI or auto-trigger on pushes!

## Current Status

Your folder structure:
```
.github/workflows/
├── Foundry/deploy.yml        ❌ Won't be auto-triggered
├── OpenAi/deploy.yml         ❌ Won't be auto-triggered
└── WORKFLOWS.md
```

## Solutions

### Option A: Manual Workflow (Recommended for now)
✅ Use GitHub Actions UI to manually trigger
- No automatic triggers on push
- Full control over which workflow runs
- Safe for testing

**Steps:**
1. Go to GitHub Repository → Actions tab
2. Select "Deploy Azure MAF Agents using Foundry" or "OpenAI"
3. Click "Run workflow"

### Option B: Copy to Root (Auto-trigger)
✅ Copy the workflow you want to root `.github/workflows/`

**For OpenAI (default):**
```bash
cp .github/workflows/OpenAi/deploy.yml .github/workflows/deploy.yml
cp .github/workflows/OpenAi/cleanup-full.yml .github/workflows/cleanup-full.yml
git add .github/workflows/deploy.yml .github/workflows/cleanup-full.yml
git commit -m "Use OpenAI deployment workflow (auto-trigger)"
git push origin master
```

**For Foundry:**
```bash
cp .github/workflows/Foundry/deploy.yml .github/workflows/deploy.yml
cp .github/workflows/Foundry/cleanup-full.yml .github/workflows/cleanup-full.yml
git add .github/workflows/deploy.yml .github/workflows/cleanup-full.yml
git commit -m "Use Foundry deployment workflow (auto-trigger)"
git push origin master
```

### Option C: Create a Selector Workflow (Advanced)
Create a root `deploy.yml` that runs the appropriate workflow based on a condition or input.

## My Recommendation

**Start with Option A (Manual Trigger):**
1. Keep both workflows in subfolders (organized)
2. Use GitHub Actions UI to test each one
3. When ready for production, copy the winning workflow to root (Option B)

This gives you:
- ✅ Flexibility to test both without changing files
- ✅ Clean organization with subfolders
- ✅ Easy to switch by copying files

## Validation

To verify workflows are discoverable:
1. Go to GitHub → Actions tab
2. You should see:
   - "Deploy Azure MAF Agents using Foundry" ✓
   - "Deploy Azure MAF Agents using Open AI" ✓
3. If you don't see them, the trigger paths in the `on:` section are wrong

## Current Trigger Configuration

**OpenAi/deploy.yml:**
```yaml
on:
  push:
    paths:
      - ".github/workflows/OpenAi/deploy.yml"  # Auto-triggers on THIS file change only
  workflow_dispatch:  # Can be triggered manually from UI
```

**Foundry/deploy.yml:**
```yaml
on:
  push:
    paths:
      - ".github/workflows/Foundry/deploy.yml"  # Auto-triggers on THIS file change only
  workflow_dispatch:  # Can be triggered manually from UI
```

Both have `workflow_dispatch` enabled, so **you can manually trigger them from GitHub Actions UI even though they're in subfolders**! ✅

## Next Steps

1. ✅ Both pipelines are configured correctly
2. ✅ Both can be manually triggered from GitHub Actions UI
3. ⏭️ Test OpenAI workflow first (safer default)
4. ⏭️ When ready for Foundry:
   - Set up Azure Foundry Hub
   - Add GitHub secrets (AZURE_FOUNDRY_ENDPOINT, AZURE_FOUNDRY_KEY)
   - Trigger Foundry workflow from Actions UI
   - Copy to root if you want auto-trigger

---

**TL;DR**: Your setup is fine! Use GitHub Actions UI to manually trigger either workflow. This is actually better for testing different deployments safely.
