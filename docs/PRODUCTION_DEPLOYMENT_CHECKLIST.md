# Production Deployment Checklist

Use this checklist before deploying to production or onboarding real users.

## ✅ Environment Separation

### Backend (Render)
- [ ] Set `ENVIRONMENT=production` in Render environment variables
- [ ] Use production Clerk instance (`CLERK_SECRET_KEY=sk_live_...`)
- [ ] Set `CLERK_FRONTEND_API` to production Clerk domain
- [ ] Use production Pinecone index (`PINECONE_INDEX_NAME=youtopia-prod`)
- [ ] Use production S3 bucket (`S3_BUCKET_NAME=youtopia-s3-prod`)
- [ ] Use production PostgreSQL database (separate Render instance)
- [ ] Set production `OPENAI_API_KEY` (separate from dev if using different billing)

### Frontend (Vercel)
- [ ] Set `VITE_API_URL` to production backend URL (e.g., `https://api.you-topia.ai`)
- [ ] Set `VITE_CLERK_PUBLISHABLE_KEY` to production key (`pk_live_...`)
- [ ] Configure custom domain: `you-topia.ai`
- [ ] Enable automatic deployments from `main` branch
- [ ] Set up preview deployments for PRs (using dev backend)

### Development Environment
- [ ] Create `.dev.env` with development credentials
- [ ] Set `ENVIRONMENT=development` in `.dev.env`
- [ ] Use development Clerk instance (`CLERK_SECRET_KEY=sk_test_...`)
- [ ] Use development Pinecone index (`PINECONE_INDEX_NAME=youtopia-dev`)
- [ ] Use development S3 bucket (`S3_BUCKET_NAME=youtopia-s3-dev`)
- [ ] Use development PostgreSQL database (can be local or Render dev instance)
- [ ] Create `frontend/.env.local` with `VITE_API_URL=http://localhost:8000`

## 🔒 Security

### Authentication & Authorization
- [ ] Separate Clerk applications for dev and prod
- [ ] Clerk webhook signing secrets configured (if using webhooks)
- [ ] Review Clerk session settings (session lifetime, MFA, etc.)
- [ ] Test multi-tenant isolation (users can't access other tenants' data)
- [ ] Verify JWT token validation is working correctly

### API Security
- [x] **CRITICAL**: Implement rate limiting ✅ DONE (slowapi v0.1.9)
- [x] File upload size limits configured ✅ DONE (50MB docs, 25MB audio)
- [x] Validate file types on upload ✅ DONE (PDF, DOCX, TXT only)
- [x] CORS origins properly configured ✅ DONE (production domains added)
- [ ] TrustedHost middleware enabled
- [x] HTTPS enforced ✅ (automatic on Vercel/Render)
- [x] Environment variables never exposed to frontend ✅ (only `VITE_*` vars)

### Data Security
- [ ] Database backups enabled on Render
- [ ] S3 bucket access restricted (not publicly accessible)
- [ ] Pinecone index access restricted to production API keys only
- [ ] Secrets stored in deployment platform (Render/Vercel), not in code
- [ ] `.env` files in `.gitignore` and never committed

## 🚀 Performance & Scalability

### Backend
- [x] Database connection pooling configured ✅ DONE (pool_size=5, max_overflow=10)
- [ ] Pinecone batch operations used where possible
- [x] S3 presigned URLs for large file downloads ✅ DONE
- [x] Async operations for I/O-bound tasks ✅ DONE
- [ ] Query optimization (indexes on frequently queried fields)

### Frontend
- [ ] Production build tested locally (`npm run build && npm run preview`)
- [ ] Bundle size optimized (code splitting, lazy loading)
- [ ] API client includes proper error handling
- [ ] Loading states for async operations

## 📊 Monitoring & Observability

### Error Tracking
- [ ] Sentry (or similar) configured for backend
- [ ] Sentry configured for frontend
- [ ] Error notifications configured (email/Slack)
- [ ] Test error reporting in production

### Logging
- [ ] Structured logging with `structlog` (already implemented ✅)
- [ ] Log levels configured (`INFO` for prod, `DEBUG` for dev)
- [ ] Sensitive data (passwords, tokens) not logged
- [ ] Log aggregation service configured (LogDNA, Datadog, etc.)

### Uptime Monitoring
- [ ] Uptime monitor configured (UptimeRobot, Pingdom, etc.)
- [ ] Health check endpoint monitored (`/health`)
- [ ] Alerts configured for downtime

### Performance Monitoring
- [ ] API response time monitoring
- [ ] Database query performance monitoring
- [ ] Pinecone query latency monitoring

## 🧪 Testing

### Pre-Deployment Testing
- [ ] All API endpoints tested with production-like data
- [ ] Authentication flow tested end-to-end
- [ ] File upload/download tested with various file types
- [ ] Error scenarios tested (network errors, invalid inputs, etc.)
- [ ] Load testing performed (if expecting high traffic)

### Post-Deployment Smoke Tests
- [ ] Health check returns 200 OK
- [ ] User can sign up/sign in
- [ ] User can upload documents
- [ ] User can create insights
- [ ] User can view training status
- [ ] All pages load without errors
- [ ] Check browser console for errors

## 📝 Documentation

- [ ] API documentation up to date
- [ ] Environment setup guide reviewed (`docs/ENVIRONMENT_SETUP.md`)
- [ ] Deployment runbook created (how to deploy, rollback, etc.)
- [ ] Incident response plan documented
- [ ] Team has access to all production credentials (in password manager)

## 🔧 Infrastructure

### Render (Backend)
- [ ] Auto-deploy enabled from `main` branch
- [ ] Health check configured (`/health` endpoint)
- [ ] Instance type appropriate for load (Standard vs Pro)
- [ ] Database backup schedule configured
- [ ] Database maintenance window configured

### Vercel (Frontend)
- [ ] Custom domain configured with SSL
- [ ] Auto-deploy enabled from `main` branch
- [ ] Preview deployments enabled for PRs
- [ ] Environment variables set for production
- [ ] Build cache optimized

## 💰 Cost Management

- [ ] OpenAI API usage limits set (to prevent billing surprises)
- [ ] Pinecone plan sufficient for expected load
- [ ] AWS S3 lifecycle policies configured (delete old files?)
- [ ] Render plan sufficient for expected traffic
- [ ] Database storage limits monitored

## 🚨 Critical Production Issues to Fix

### ✅ COMPLETED

1. **~~Add Rate Limiting~~** ✅ DONE
   - Added slowapi==0.1.9 to requirements.txt
   - Configured global rate limiter in server.py
   - Applied limits: 10/min document uploads, 30/min text insights, 20/min voice
   - Protects against API abuse and DDoS attacks

2. **~~File Upload Size Limits~~** ✅ DONE
   - Documents: Max 50MB per file, max 10 files per request
   - Voice: Max 25MB per file
   - Empty file detection
   - Clear error messages (HTTP 413)

3. **~~Database Connection Pooling~~** ✅ DONE
   - pool_size=5, max_overflow=10
   - pool_pre_ping=True for connection validation
   - Prevents connection exhaustion

### HIGH PRIORITY (Before onboarding real users)

4. **Separate Clerk Instances** 🔴
   - Create separate Clerk applications for dev and prod
   - Update environment variables accordingly
   - Status: User confirmed this is already configured

### MEDIUM PRIORITY (Fix within first week of production)

5. **Error Monitoring**
   - Set up Sentry for production error tracking
   - Configure alerts

6. **Uptime Monitoring**
   - Set up external uptime monitor
   - Configure downtime alerts

7. **CORS Configuration**
   - Make CORS origins environment-aware
   - Remove localhost from production

### LOW PRIORITY (Nice to have)

8. **Performance Monitoring**
   - Add APM (Application Performance Monitoring)
   - Track slow queries

9. **Analytics**
   - User analytics (if desired)
   - Usage metrics

## 📞 Rollback Plan

If something goes wrong in production:

1. **Immediate**: Use Render/Vercel dashboard to rollback to previous deployment
2. **Vercel**: Go to Deployments → Click previous successful deployment → "Promote to Production"
3. **Render**: Go to deployment history → Click previous deployment → "Redeploy"
4. **Database**: If database migration failed, have rollback SQL ready
5. **Communication**: Notify users via status page/email if downtime > 5 minutes

## ✅ Final Sign-Off

Before going live:

- [ ] All HIGH PRIORITY items from "Critical Production Issues" are resolved
- [ ] Team has reviewed and approved the deployment
- [ ] Rollback plan tested
- [ ] On-call rotation scheduled (who responds to production issues)
- [ ] Backup restore procedure tested

---

**Last Updated**: 2025-12-22 (Updated after implementing rate limiting and file size limits)
**Next Review**: Before first production deployment

## Recent Updates (2025-12-22)

**Implemented:**
- ✅ Rate limiting with slowapi (10/min uploads, 30/min text insights, 20/min voice)
- ✅ File upload size limits (50MB docs, 25MB audio)
- ✅ Enhanced file validation (empty file detection, file count limits)
- ✅ Database connection pooling (already implemented in db.py)
- ✅ CORS error handling (already implemented in server.py)
- ✅ Clerk authentication integration (already implemented in client.ts)

**Status:** Ready for production deployment pending:
1. Clerk instance separation verification (user confirmed already done)
2. Error monitoring setup (Sentry - recommended)
3. Uptime monitoring setup (UptimeRobot - recommended)
