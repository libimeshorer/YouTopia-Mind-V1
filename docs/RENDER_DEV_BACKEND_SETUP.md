# Setting Up Development Backend on Render

## Overview

This guide shows how to create a separate development backend service on Render to work alongside your production backend. This allows you to test the full end-to-end flow with development resources (dev PostgreSQL, dev Pinecone, dev S3) without affecting production.

## Why You Need Two Separate Services

Render web services don't have "development" and "production" environments within a single service. Instead, you create **two separate web services**:

1. **Production Backend** - Points to prod database, prod Pinecone, prod S3
2. **Development Backend** - Points to dev database, dev Pinecone, dev S3

Both services run the **same code** from your repository, but use **different environment variables**.

---

## Step-by-Step Setup

### Step 1: Identify Your Current Production Service

1. Go to https://dashboard.render.com
2. Find your existing backend service (e.g., `youtopia-backend`)
3. Note its settings - you'll replicate these for dev

### Step 2: Create New Development Web Service

1. In Render Dashboard, click **"New +"** → **"Web Service"**

2. **Connect Your Repository:**
   - Select the same GitHub repository you used for production
   - Repository: `YouTopia-Mind-V1`

3. **Configure the Service:**

   | Setting | Value | Notes |
   |---------|-------|-------|
   | **Name** | `youtopia-backend-dev` | Must be different from prod service |
   | **Region** | Same as production | For consistency |
   | **Branch** | `main` or `develop` | Can use same branch as prod or a dev branch |
   | **Root Directory** | (leave blank or same as prod) | |
   | **Runtime** | `Python 3` | Same as production |
   | **Build Command** | `pip install -r requirements.txt` | Same as production |
   | **Start Command** | `uvicorn src.api.server:app --host 0.0.0.0 --port $PORT` | Same as production |
   | **Plan** | `Starter` or `Free` | Free tier is fine for dev |

4. Click **"Create Web Service"**

### Step 3: Configure Development Environment Variables

Once the service is created, go to **Environment** tab and add:

#### Required Variables

```bash
# Environment Identifier
ENVIRONMENT=development

# Clerk Development Keys
CLERK_SECRET_KEY=sk_test_XXXXXXXXXXXXXXXXXXXXX

# PostgreSQL - DEV DATABASE
DATABASE_URL=postgresql://user:pass@dpg-XXXXX-dev.render.com:5432/youtopia_dev

# Pinecone - DEV INDEX
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=youtopia-dev

# AWS S3 - DEV BUCKET
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=youtopia-s3-dev

# OpenAI (can be same as prod)
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXX
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Optional Settings
LOG_LEVEL=DEBUG
```

**Critical:**
- Use `sk_test_` Clerk key (development environment)
- Point to dev PostgreSQL database
- Point to dev Pinecone index (`youtopia-dev`)
- Point to dev S3 bucket (`youtopia-s3-dev`)

### Step 4: Get Your Dev Backend URL

After deployment completes:

1. Go to your dev service in Render
2. At the top, you'll see the URL:
   - Default: `https://youtopia-backend-dev.onrender.com`
   - Or you can add a custom domain: `api-dev.you-topia.ai`

3. **Copy this URL** - this is your `VITE_API_URL` for development!

### Step 5: Test Your Dev Backend

```bash
# Health check
curl https://youtopia-backend-dev.onrender.com/health

# Should return:
# {"status": "healthy", "environment": "development"}
```

---

## Connecting Frontend to Dev Backend

Now that you have a dev backend URL, configure your frontend:

### For Local Development

Create `frontend/.env.local`:

```bash
# Clerk Development
VITE_CLERK_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXX

# Point to dev backend on Render
VITE_API_URL=https://youtopia-backend-dev.onrender.com
```

**Test locally:**

```bash
cd frontend
npm run dev

# Your local frontend (localhost:8080) will now connect to:
# - Clerk Development environment (pk_test_)
# - Dev backend on Render (youtopia-backend-dev)
# - Dev PostgreSQL database
# - Dev Pinecone index
# - Dev S3 bucket
```

### For Vercel Preview Deployments

In **Vercel → Settings → Environment Variables**:

| Variable | Value | Environments |
|----------|-------|--------------|
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_XXXXX` | ✅ Preview, ✅ Development |
| `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_XXXXX` | ✅ Production |
| `VITE_API_URL` | `https://youtopia-backend-dev.onrender.com` | ✅ Preview, ✅ Development |
| `VITE_API_URL` | `https://api.you-topia.ai` | ✅ Production |

**Result:**
- Preview deployments → Dev backend → Dev resources
- Production deployment → Prod backend → Prod resources

---

## Architecture Overview

### Development Flow

```
Developer/Preview Deployment
    ↓
Frontend (localhost:8080 or preview.vercel.app)
    ↓ (Uses pk_test_xxx)
    ↓
Clerk Development Environment
    ↓
    ↓ (Makes API calls with Bearer token)
    ↓
Dev Backend (youtopia-backend-dev.onrender.com)
    ↓ (Verifies with sk_test_xxx)
    ↓ (ENVIRONMENT=development)
    ↓
    ├─→ Dev PostgreSQL (dpg-XXXXX-dev.render.com)
    ├─→ Dev Pinecone (youtopia-dev index)
    └─→ Dev S3 (youtopia-s3-dev bucket)
```

### Production Flow

```
User
    ↓
Frontend (you-topia.ai)
    ↓ (Uses pk_live_xxx)
    ↓
Clerk Production Environment
    ↓
    ↓ (Makes API calls with Bearer token)
    ↓
Prod Backend (api.you-topia.ai)
    ↓ (Verifies with sk_live_xxx)
    ↓ (ENVIRONMENT=production)
    ↓
    ├─→ Prod PostgreSQL (dpg-XXXXX-prod.render.com)
    ├─→ Prod Pinecone (youtopia-prod index)
    └─→ Prod S3 (youtopia-s3-prod bucket)
```

---

## Managing Two Services

### Deployment Strategy

Both services deploy from the same repository:

**Option 1: Same Branch (Simpler)**
- Both prod and dev deploy from `main` branch
- Use environment variables to differentiate
- Push to `main` → Both services redeploy automatically

**Option 2: Separate Branches (More Control)**
- Prod service deploys from `main` branch
- Dev service deploys from `develop` branch
- Test in `develop` first, then merge to `main`

### Cost Considerations

**Free Tier:**
- Render allows multiple free web services
- Free services spin down after inactivity (takes 30s to spin up on next request)
- Fine for development/testing

**Paid Tier:**
- If you upgrade prod to paid ($7/month), dev can stay free
- Or upgrade both for always-on services

### Monitoring Both Services

In Render Dashboard:
- You'll see both services listed
- Each has its own logs, metrics, and settings
- Deploy them independently

---

## Verifying Isolation

### Test Development Environment

1. **Visit frontend with dev backend:**
   - Local: `http://localhost:8080` (with `VITE_API_URL=https://youtopia-backend-dev.onrender.com`)
   - Or Vercel preview deployment

2. **Sign up with test account:**
   - Uses `pk_test_` → Clerk Development environment

3. **Create clone, upload documents:**
   - Backend uses `DATABASE_URL` → Dev PostgreSQL
   - Backend uses `PINECONE_INDEX_NAME=youtopia-dev` → Dev Pinecone
   - Backend uses `S3_BUCKET_NAME=youtopia-s3-dev` → Dev S3

4. **Verify data isolation:**
   ```bash
   # Check Clerk
   # - Go to Clerk Dashboard → Switch to Development
   # - Should see your test user

   # Check PostgreSQL
   psql $DEV_DATABASE_URL
   SELECT * FROM clones;  # Should see your test clone
   \q

   # Check production is clean
   # - Clerk Production environment: No test users
   # - Prod PostgreSQL: No test data
   # - Prod Pinecone: No test vectors
   ```

---

## Troubleshooting

### Service creation keeps defaulting to production settings

This isn't a Render "production" environment - it's just that Render doesn't have environment presets. When you create a new service:
1. Give it a **different name** (e.g., `youtopia-backend-dev`)
2. Manually set **all environment variables** to development values
3. That's what makes it "development" - the environment variables, not a Render setting

### Can't afford two services

**Options:**
1. Keep dev service on free tier (spins down when inactive)
2. Use local backend for development:
   - Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local`
   - Run backend locally with `ENVIRONMENT=development`
   - Only use Render for production

### Frontend can't connect to backend

**Common issues:**
1. **CORS:** Check backend allows frontend domain
2. **HTTPS:** Render services use HTTPS by default
3. **Spin-up time:** Free tier services take 30s to wake up
4. **Wrong URL:** Double-check `VITE_API_URL` in frontend

**Check backend logs:**
- Render Dashboard → Your dev service → Logs
- Look for startup messages: "Environment: development"

### Backend using wrong database

**Verify environment variables:**
```bash
# In Render Dashboard → Service → Environment tab
# Check these are set correctly:
ENVIRONMENT=development
DATABASE_URL=postgresql://...dev-db...
PINECONE_INDEX_NAME=youtopia-dev
S3_BUCKET_NAME=youtopia-s3-dev
```

After changing env vars, service will auto-redeploy.

---

## Custom Domains (Optional)

### Set Up Custom Domain for Dev Backend

1. **Add subdomain DNS record:**
   - Type: `CNAME`
   - Name: `api-dev`
   - Value: `youtopia-backend-dev.onrender.com`
   - TTL: `3600`

2. **In Render:**
   - Go to dev service → Settings → Custom Domain
   - Add: `api-dev.you-topia.ai`
   - Render will provision SSL certificate automatically

3. **Update frontend:**
   ```bash
   # frontend/.env.local or Vercel env vars
   VITE_API_URL=https://api-dev.you-topia.ai
   ```

### Result

- Production: `api.you-topia.ai` → Prod backend → Prod resources
- Development: `api-dev.you-topia.ai` → Dev backend → Dev resources

---

## Alternative: Single Backend with Environment Detection

If you **really** don't want two services, you can use one backend that switches based on a request header:

**Not recommended because:**
- More complex code
- Higher risk of mixing environments
- Harder to debug
- No cost savings (still need dev database, Pinecone, S3)

**If you must:**
1. Keep one backend service
2. Add environment detection logic
3. Pass environment identifier from frontend
4. Backend switches resources based on identifier

But **two separate services is much cleaner and safer**.

---

## Summary

### What You Need to Do

1. ✅ Create second Render web service: `youtopia-backend-dev`
2. ✅ Configure with development environment variables
3. ✅ Get the dev backend URL: `https://youtopia-backend-dev.onrender.com`
4. ✅ Set `VITE_API_URL` in frontend to point to dev backend
5. ✅ Test full E2E flow
6. ✅ Verify production is untouched

### Your Complete Setup

| Component | Development | Production |
|-----------|-------------|------------|
| **Frontend** | localhost:8080 or Vercel preview | you-topia.ai |
| **Backend** | youtopia-backend-dev.onrender.com | api.you-topia.ai |
| **Clerk** | pk_test_ / sk_test_ | pk_live_ / sk_live_ |
| **PostgreSQL** | Dev database on Render | Prod database on Render |
| **Pinecone** | youtopia-dev index | youtopia-prod index |
| **S3** | youtopia-s3-dev bucket | youtopia-s3-prod bucket |

---

## Related Documentation

- [E2E Development Testing](./E2E_DEV_TESTING.md)
- [Clerk Dev/Prod Setup](./CLERK_DEV_PROD_SETUP.md)
- [Vercel Dev Deployment](./VERCEL_DEV_DEPLOYMENT.md)
- [Environment Setup Guide](./ENVIRONMENT_SETUP.md)
