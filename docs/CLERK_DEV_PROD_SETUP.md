# Clerk Development vs Production Setup

## Your Current Setup (Recommended)

You have a single Clerk application "YouTopia" with both Development and Production environments. This is the **ideal setup** - you don't need a separate application.

## Getting Your Keys from Clerk

### Step 1: Access Clerk Dashboard

1. Go to https://dashboard.clerk.com
2. Select your "YouTopia" application

### Step 2: Get Development Keys

1. In the Clerk dashboard, look for the **environment switcher** (usually top-left or top-right)
2. Switch to **"Development"** environment
3. Go to **API Keys** section
4. Copy:
   - **Publishable Key** (starts with `pk_test_`)
   - **Secret Key** (starts with `sk_test_`)

### Step 3: Get Production Keys

1. Switch to **"Production"** environment in Clerk
2. Go to **API Keys** section
3. Copy:
   - **Publishable Key** (starts with `pk_live_`)
   - **Secret Key** (starts with `sk_live_`)

---

## Environment Configuration

### Frontend Development (Local Testing)

Create `frontend/.env.local`:

```bash
# Use Clerk DEVELOPMENT keys for local testing
VITE_CLERK_PUBLISHABLE_KEY=pk_test_XXXXXXXXXXXXXXXXXXXXX

# Optional: Point to local backend
VITE_API_URL=http://localhost:8000
```

### Frontend Production (Vercel)

In **Vercel → Settings → Environment Variables**:

```bash
# Production environment
VITE_CLERK_PUBLISHABLE_KEY=pk_live_XXXXXXXXXXXXXXXXXXXXX  # ← Production key
VITE_API_URL=https://api.you-topia.ai
```

### Backend Development

Create `.dev.env` in project root:

```bash
ENVIRONMENT=development

# Clerk DEVELOPMENT credentials
CLERK_SECRET_KEY=sk_test_XXXXXXXXXXXXXXXXXXXXX

# Dev database
DATABASE_URL=postgresql://user:pass@dpg-dev.render.com:5432/youtopia_dev

# Dev resources
PINECONE_INDEX_NAME=youtopia-dev
S3_BUCKET_NAME=youtopia-s3-dev

# Other credentials (can be shared or separate)
OPENAI_API_KEY=sk-xxxxx
PINECONE_API_KEY=xxxxx
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
```

### Backend Production

Create `.prod.env` in project root:

```bash
ENVIRONMENT=production

# Clerk PRODUCTION credentials
CLERK_SECRET_KEY=sk_live_XXXXXXXXXXXXXXXXXXXXX

# Production database
DATABASE_URL=postgresql://user:pass@dpg-prod.render.com:5432/youtopia_prod

# Production resources
PINECONE_INDEX_NAME=youtopia-prod
S3_BUCKET_NAME=youtopia-s3-prod

# Other credentials
OPENAI_API_KEY=sk-xxxxx
PINECONE_API_KEY=xxxxx
AWS_ACCESS_KEY_ID=xxxxx
AWS_SECRET_ACCESS_KEY=xxxxx
```

---

## How This Works

### Development Flow

```
Developer's Browser (localhost:8080)
    ↓
    ↓ (Uses pk_test_xxx)
    ↓
Clerk Development Instance
    ↓
    ↓ (User authenticated)
    ↓
Backend API (localhost:8000)
    ↓ (Verifies with sk_test_xxx)
    ↓
    ├─→ Dev PostgreSQL (Render)
    ├─→ Dev Pinecone Index (youtopia-dev)
    └─→ Dev S3 Bucket (youtopia-s3-dev)
```

### Production Flow

```
User's Browser (you-topia.ai)
    ↓
    ↓ (Uses pk_live_xxx)
    ↓
Clerk Production Instance
    ↓
    ↓ (User authenticated)
    ↓
Backend API (api.you-topia.ai)
    ↓ (Verifies with sk_live_xxx)
    ↓
    ├─→ Prod PostgreSQL (Render)
    ├─→ Prod Pinecone Index (youtopia-prod)
    └─→ Prod S3 Bucket (youtopia-s3-prod)
```

---

## Key Benefits of Your Setup

### ✅ Single Application, Multiple Environments

- Users in dev environment are **separate** from production users
- Sessions don't cross environments
- Authentication settings can be configured per environment
- All in one Clerk application for easy management

### ✅ Proper Isolation

When you use:
- `pk_test_` + `sk_test_` → Users go to Development environment
- `pk_live_` + `sk_live_` → Users go to Production environment

These are **completely isolated**:
- A user in dev won't appear in production
- Sessions don't carry over
- Email addresses can be reused across environments

---

## Testing Locally with Dev Environment

### Step 1: Configure Frontend

```bash
# frontend/.env.local
VITE_CLERK_PUBLISHABLE_KEY=pk_test_YOUR_DEV_KEY_HERE
```

### Step 2: Configure Backend

```bash
# Export environment
export ENVIRONMENT=development

# Backend will load .dev.env automatically (via src/config/settings.py)
```

### Step 3: Start Services

```bash
# Terminal 1: Backend
export ENVIRONMENT=development
uvicorn src.api.server:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Step 4: Test

1. Visit http://localhost:8080
2. Sign up with test credentials
3. Create clones, upload documents
4. **All data goes to dev resources**:
   - Users → Clerk Development environment
   - Database → Dev PostgreSQL
   - Embeddings → Dev Pinecone index
   - Files → Dev S3 bucket

---

## Verifying Your Setup

### Check Clerk Environment

In Clerk dashboard:
1. Switch between Development and Production using environment switcher
2. Go to Users section
3. Verify users created in dev **don't appear** in production

### Check Backend Logs

When starting backend, you should see:

```bash
INFO:     Environment: development
INFO:     Pinecone Index: youtopia-dev
INFO:     S3 Bucket: youtopia-s3-dev
INFO:     Database: dpg-dev.render.com
```

### Check Frontend Console

In browser console (F12), you should see:

```
[Clerk Config] ✅ Clerk publishable key loaded successfully
{
  keyPrefix: "pk_test_...",
  isTestKey: true,
  environment: "development"
}
```

---

## Common Mistakes to Avoid

### ❌ Don't Mix Keys

```bash
# WRONG - Don't do this!
frontend/.env.local:
  VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx  # Dev key

.prod.env:
  CLERK_SECRET_KEY=sk_live_xxx  # Prod secret
```

This will cause authentication failures because the frontend uses dev environment but backend expects production users.

### ✅ Match Keys to Environment

```bash
# CORRECT - Development
frontend/.env.local:
  VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx

.dev.env:
  CLERK_SECRET_KEY=sk_test_xxx

# CORRECT - Production
Vercel env vars:
  VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx

.prod.env (or Render env vars):
  CLERK_SECRET_KEY=sk_live_xxx
```

---

## Environment Variables Cheat Sheet

### Local Development

| Service | Variable | Value |
|---------|----------|-------|
| Frontend | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_...` |
| Backend | `CLERK_SECRET_KEY` | `sk_test_...` |
| Backend | `ENVIRONMENT` | `development` |
| Backend | `DATABASE_URL` | Dev PostgreSQL URL |
| Backend | `PINECONE_INDEX_NAME` | `youtopia-dev` |
| Backend | `S3_BUCKET_NAME` | `youtopia-s3-dev` |

### Production (Vercel + Render)

| Service | Variable | Value |
|---------|----------|-------|
| Vercel (Frontend) | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_live_...` |
| Render (Backend) | `CLERK_SECRET_KEY` | `sk_live_...` |
| Render (Backend) | `ENVIRONMENT` | `production` |
| Render (Backend) | `DATABASE_URL` | Prod PostgreSQL URL |
| Render (Backend) | `PINECONE_INDEX_NAME` | `youtopia-prod` |
| Render (Backend) | `S3_BUCKET_NAME` | `youtopia-s3-prod` |

---

## Next Steps

1. **Get your keys:**
   - Go to Clerk dashboard
   - Switch to Development environment
   - Copy `pk_test_` and `sk_test_` keys

2. **Set up local development:**
   - Create `frontend/.env.local` with `pk_test_` key
   - Create `.dev.env` with `sk_test_` key and dev resources

3. **Test locally:**
   - Start backend with `ENVIRONMENT=development`
   - Start frontend with `npm run dev`
   - Sign up and test full flow

4. **Verify isolation:**
   - Check Clerk dashboard (Development vs Production users)
   - Check database (dev vs prod databases)
   - Verify no cross-contamination

---

## Troubleshooting

### "Invalid Clerk session" errors

**Cause:** Mismatched keys (frontend using `pk_test_` but backend using `sk_live_`)

**Solution:** Ensure both frontend and backend use matching environment keys:
- Dev: `pk_test_` + `sk_test_`
- Prod: `pk_live_` + `sk_live_`

### Users appearing in wrong environment

**Cause:** Using wrong publishable key in frontend

**Solution:**
- Local dev: Use `pk_test_` in `frontend/.env.local`
- Production: Use `pk_live_` in Vercel env vars

### Can't find environment switcher in Clerk

**Location:** Usually in top-left or top-right of Clerk dashboard, shows current environment (Development/Production)

If you don't see it, you might only have one environment. Check:
- Settings → Environments
- You should see both Development and Production listed

---

## Additional Resources

- [Clerk Documentation - Environments](https://clerk.com/docs/deployments/environments)
- [E2E Development Testing Guide](./E2E_DEV_TESTING.md)
- [Environment Setup Guide](./ENVIRONMENT_SETUP.md)
- [Local Testing Guide](./LOCAL_TESTING.md)
