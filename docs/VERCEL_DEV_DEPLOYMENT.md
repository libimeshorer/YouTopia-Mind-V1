# Vercel Development Deployment Setup

## Overview

This guide shows how to set up a **development version** of your you-topia.ai application on Vercel for testing the full end-to-end flow with the same code as production, but using development resources (dev database, dev Pinecone, dev S3).

## Vercel's Three Deployment Types

Vercel automatically creates three types of deployments:

1. **Production** - `you-topia.ai` (main branch)
2. **Preview** - Unique URL for each PR/branch (e.g., `you-topia-git-feature-branch.vercel.app`)
3. **Development** - Local development with `vercel dev`

---

## Option 1: Use Preview Deployments for Dev Testing (RECOMMENDED)

This is the easiest and most common approach.

### How It Works

Every time you push to a non-main branch, Vercel automatically creates a **Preview Deployment** with:
- Unique URL: `you-topia-git-BRANCH-NAME-USERNAME.vercel.app`
- Can use different environment variables than production
- Same codebase, different configuration
- Perfect for testing before merging to main

### Setup Steps

#### Step 1: Configure Preview Environment Variables in Vercel

1. Go to **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**

2. Add your **development** Clerk key for Preview environment:

   | Key | Value | Environments |
   |-----|-------|--------------|
   | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_YOUR_DEV_KEY` | ✅ Preview, ✅ Development |
   | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_YOUR_PROD_KEY` | ✅ Production |
   | `VITE_API_URL` | `https://api-dev.you-topia.ai` | ✅ Preview, ✅ Development |
   | `VITE_API_URL` | `https://api.you-topia.ai` | ✅ Production |

   **Important:**
   - Same variable name, different values for different environments
   - Vercel will use the appropriate value based on deployment type
   - Preview/Development use `pk_test_` (Clerk dev environment)
   - Production uses `pk_live_` (Clerk prod environment)

#### Step 2: Set Up Backend for Preview Environment

Since your backend likely runs on Render, you have two options:

**Option A: Separate Dev Backend Service on Render**

1. Create a new Web Service on Render: `youtopia-api-dev`
2. Configure environment variables:
   ```bash
   ENVIRONMENT=development
   CLERK_SECRET_KEY=sk_test_YOUR_DEV_KEY
   DATABASE_URL=postgresql://...your-dev-db...
   PINECONE_INDEX_NAME=youtopia-dev
   S3_BUCKET_NAME=youtopia-s3-dev
   ```
3. Deploy to URL: `https://youtopia-api-dev.onrender.com` (or custom domain `https://api-dev.you-topia.ai`)
4. Use this URL in Vercel Preview env var: `VITE_API_URL=https://api-dev.you-topia.ai`

**Option B: Use Same Backend with Environment Detection**

If your backend can detect which environment to use based on the request:
1. Add logic to detect dev vs prod (e.g., based on origin domain)
2. Route to appropriate resources accordingly
3. Less clean, but requires fewer services

**Recommendation:** Use Option A (separate dev backend) for cleaner isolation.

#### Step 3: Test Preview Deployment

1. **Create a test branch:**
   ```bash
   git checkout -b test/dev-deployment
   git push origin test/dev-deployment
   ```

2. **Vercel automatically deploys:**
   - Check Vercel dashboard → Deployments
   - You'll see a new Preview deployment
   - URL: `you-topia-git-test-dev-deployment-YOUR-USERNAME.vercel.app`

3. **Test the deployment:**
   - Visit the preview URL
   - Sign up (uses Clerk dev environment with `pk_test_` key)
   - Create clones (saved to dev PostgreSQL)
   - Upload documents (saved to dev S3 + Pinecone)
   - Chat (queries dev Pinecone index)

4. **Verify isolation:**
   - Check Clerk dashboard → Development environment (users should appear here)
   - Check dev PostgreSQL database (clones and data should be here)
   - Production is untouched ✅

#### Step 4: Configure Custom Preview Domain (Optional)

For cleaner URLs, you can set up:
- `dev.you-topia.ai` → Points to your latest preview deployment
- Or use Vercel's automatic preview URLs

In Vercel:
1. Settings → Domains
2. Add `dev.you-topia.ai`
3. Configure to point to preview deployments

---

## Option 2: Separate Vercel Project for Development

If you want a persistent dev deployment (not tied to branches):

### Setup Steps

1. **Create a new Vercel project:**
   - Import the same GitHub repository
   - Name it: `YouTopia-Mind-Dev`
   - Configure to deploy from a `develop` or `staging` branch

2. **Configure environment variables:**
   ```bash
   VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_DEV_KEY
   VITE_API_URL=https://api-dev.you-topia.ai
   ```

3. **Set up custom domain:**
   - `dev.you-topia.ai` → Points to this project
   - Persistent dev environment

4. **Workflow:**
   ```bash
   # Make changes
   git checkout develop
   git commit -m "feat: new feature"
   git push origin develop

   # Vercel deploys to dev.you-topia.ai
   # Test thoroughly

   # When ready, merge to main
   git checkout main
   git merge develop
   git push origin main

   # Vercel deploys to you-topia.ai (production)
   ```

### Pros & Cons

**Option 2 (Separate Project):**
- ✅ Persistent dev URL (`dev.you-topia.ai`)
- ✅ Clear separation
- ❌ Two projects to manage
- ❌ Uses more Vercel project quota

**Option 1 (Preview Deployments):**
- ✅ Automatic, no extra setup
- ✅ One project
- ✅ URL per branch/PR
- ❌ URLs are longer
- ❌ Preview deployments expire after inactivity

---

## Recommended Architecture

### Development Flow

```
Developer → Pushes to branch
    ↓
Vercel Preview Deployment
    URL: you-topia-git-BRANCH.vercel.app
    Uses: pk_test_xxx (Clerk dev)
    ↓
Backend Dev Service (Render)
    URL: api-dev.you-topia.ai
    Uses: sk_test_xxx (Clerk dev)
    ↓
    ├─→ Dev PostgreSQL
    ├─→ Dev Pinecone (youtopia-dev)
    └─→ Dev S3 (youtopia-s3-dev)
```

### Production Flow

```
Developer → Merges to main
    ↓
Vercel Production Deployment
    URL: you-topia.ai
    Uses: pk_live_xxx (Clerk prod)
    ↓
Backend Prod Service (Render)
    URL: api.you-topia.ai
    Uses: sk_live_xxx (Clerk prod)
    ↓
    ├─→ Prod PostgreSQL
    ├─→ Prod Pinecone (youtopia-prod)
    └─→ Prod S3 (youtopia-s3-prod)
```

---

## Environment Variables Setup in Vercel

### Complete Configuration

Go to **Vercel → Settings → Environment Variables** and add:

| Variable Name | Production Value | Preview Value | Development Value |
|---------------|------------------|---------------|-------------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_XXX` | `pk_test_XXX` | `pk_test_XXX` |
| `VITE_API_URL` | `https://api.you-topia.ai` | `https://api-dev.you-topia.ai` | `http://localhost:8000` |

**How to add different values per environment:**

1. Add variable: `VITE_CLERK_PUBLISHABLE_KEY`
2. Click "Add" for first value:
   - Value: `pk_live_XXXXX`
   - Check: ✅ Production
   - Click "Save"
3. Click "Add" again for second value:
   - Value: `pk_test_XXXXX`
   - Check: ✅ Preview, ✅ Development
   - Click "Save"

Now Vercel will use the correct key based on deployment type!

---

## Backend Setup on Render

### Create Dev Web Service

1. **New Web Service:**
   - Name: `youtopia-api-dev`
   - Branch: Can use same branch as prod, or use `develop` branch
   - Build Command: Same as production
   - Start Command: Same as production

2. **Environment Variables:**
   ```bash
   ENVIRONMENT=development

   # Clerk Dev
   CLERK_SECRET_KEY=sk_test_XXXXXXXXXXXXX

   # Dev Resources
   DATABASE_URL=postgresql://...dev-db-url...
   PINECONE_INDEX_NAME=youtopia-dev
   S3_BUCKET_NAME=youtopia-s3-dev

   # Shared Credentials
   OPENAI_API_KEY=sk-xxxxx
   PINECONE_API_KEY=xxxxx
   AWS_ACCESS_KEY_ID=xxxxx
   AWS_SECRET_ACCESS_KEY=xxxxx
   AWS_REGION=us-east-1
   ```

3. **Custom Domain (optional):**
   - Add `api-dev.you-topia.ai`
   - Points to this dev service

---

## Testing Your Setup

### Step 1: Trigger a Preview Deployment

```bash
# Create a test branch
git checkout -b test/preview-deployment
echo "// test change" >> frontend/src/App.tsx
git add .
git commit -m "test: Trigger preview deployment"
git push origin test/preview-deployment
```

### Step 2: Find Your Preview URL

1. Go to Vercel Dashboard → Deployments
2. Find the deployment for your branch
3. Click to get the URL (e.g., `you-topia-git-test-preview-deployment.vercel.app`)

### Step 3: Test End-to-End

1. **Visit preview URL**
2. **Sign up** with test email
3. **Check Clerk:** User should appear in Development environment
4. **Create clone:** Should save to dev PostgreSQL
5. **Upload docs:** Should go to dev S3 + Pinecone
6. **Chat:** Should query dev Pinecone index

### Step 4: Verify Isolation

**Check that production is untouched:**
- Clerk Production environment: No new users
- Production PostgreSQL: No test data
- Production Pinecone: No test vectors
- Production S3: No test files

**Check that dev has your test data:**
- Clerk Development environment: Your test user exists
- Dev PostgreSQL: Your clone exists
- Dev Pinecone: Your document vectors exist
- Dev S3: Your files exist

---

## Troubleshooting

### Preview deployment uses production keys

**Problem:** Preview deployment authenticates against Clerk production

**Solution:**
1. Check Vercel → Settings → Environment Variables
2. Ensure `VITE_CLERK_PUBLISHABLE_KEY` has separate values:
   - Production: `pk_live_xxx` (checked for "Production" only)
   - Preview: `pk_test_xxx` (checked for "Preview" and "Development")
3. Redeploy preview (push new commit or click "Redeploy" in Vercel)

### Preview can't connect to backend

**Problem:** `VITE_API_URL` not set correctly

**Solution:**
1. Add `VITE_API_URL` in Vercel environment variables:
   - Preview: `https://api-dev.you-topia.ai` (or your dev backend URL)
   - Production: `https://api.you-topia.ai`
2. Redeploy

### Backend returns 401/403 errors

**Problem:** Backend is using production Clerk secret, frontend is using dev key

**Solution:**
1. Ensure your dev backend service on Render has `CLERK_SECRET_KEY=sk_test_xxx`
2. Frontend preview should use `VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx`
3. Keys must match (both test or both live)

---

## Best Practices

### 1. Always Test in Preview Before Merging to Main

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes, push
git push origin feature/new-feature

# Test preview deployment thoroughly
# - Sign up
# - Create clone
# - Upload docs
# - Chat

# If all works, merge to main
git checkout main
git merge feature/new-feature
git push origin main

# Production deployment happens automatically
```

### 2. Use Branch Protection Rules

In GitHub:
1. Settings → Branches → Add rule for `main`
2. Require status checks (Vercel preview deployment must succeed)
3. Require reviews before merging
4. Ensures production only gets tested code

### 3. Monitor Both Environments

- Dev: Monitor for bugs, test new features
- Prod: Monitor for performance, user issues

### 4. Clean Up Dev Environment Regularly

```bash
# Periodically clean dev resources
# - Remove test users from Clerk dev environment
# - Clean up dev PostgreSQL test data
# - Delete test documents from dev S3
# - Clear test vectors from dev Pinecone

python scripts/cleanup_dev_environment.py
```

---

## Quick Reference

### Environment URLs

| Environment | Frontend | Backend | Database | Pinecone | S3 |
|-------------|----------|---------|----------|----------|-----|
| Production | `you-topia.ai` | `api.you-topia.ai` | Prod PostgreSQL | `youtopia-prod` | `youtopia-s3-prod` |
| Preview/Dev | `*-git-*.vercel.app` | `api-dev.you-topia.ai` | Dev PostgreSQL | `youtopia-dev` | `youtopia-s3-dev` |
| Local | `localhost:8080` | `localhost:8000` | Local PostgreSQL | `youtopia-dev` | `youtopia-s3-dev` |

### Clerk Keys

| Environment | Frontend Key | Backend Secret |
|-------------|--------------|----------------|
| Production | `pk_live_xxx` | `sk_live_xxx` |
| Dev/Preview | `pk_test_xxx` | `sk_test_xxx` |

---

## Next Steps

1. **Set up Vercel environment variables:**
   - Add `VITE_CLERK_PUBLISHABLE_KEY` with separate values for prod/preview
   - Add `VITE_API_URL` with separate backend URLs

2. **Set up dev backend on Render:**
   - Create `youtopia-api-dev` web service
   - Configure with development environment variables
   - Deploy and test

3. **Test preview deployment:**
   - Push to a test branch
   - Visit preview URL
   - Test full E2E flow
   - Verify dev resources used

4. **Document your workflow:**
   - Share with team
   - Update PR templates with testing checklist
   - Create runbooks for common tasks

---

## Related Documentation

- [Clerk Dev/Prod Setup](./CLERK_DEV_PROD_SETUP.md)
- [E2E Development Testing](./E2E_DEV_TESTING.md)
- [Environment Setup Guide](./ENVIRONMENT_SETUP.md)
- [Vercel Documentation - Preview Deployments](https://vercel.com/docs/deployments/preview-deployments)
