# Environment Variables Setup

## Local Development (.env.local)

Create a `.env.local` file in the project root with the following variables:

```bash
# Database (SQLite for local development)
DATABASE_URL=sqlite:///./data/youtopia.db

# Clerk Authentication
CLERK_SECRET_KEY=sk_test_...
CLERK_FRONTEND_API=https://your-clerk-domain.clerk.accounts.dev
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_AUDIENCE=your-clerk-audience

# Pinecone Vector Database
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=youtopia-dev

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# AWS S3
S3_BUCKET_NAME=youtopia-mind-data
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Slack (optional, for Slack bot functionality)
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## Render Production Environment Variables

Set these in the Render dashboard for your Web Service:

- `DATABASE_URL` - Auto-provided by Render PostgreSQL
- `CLERK_SECRET_KEY` - Your Clerk secret key
- `CLERK_FRONTEND_API` - Your Clerk frontend API URL
- `CLERK_ISSUER` - Your Clerk issuer URL
- `CLERK_AUDIENCE` - Your Clerk audience
- `PINECONE_API_KEY` - Production Pinecone API key
- `PINECONE_INDEX_NAME=youtopia-prod`
- `OPENAI_API_KEY` - Your OpenAI API key
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-large`
- `S3_BUCKET_NAME` - Your S3 bucket name
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION=us-east-1`
- `VERCEL_URL` - Your Vercel domain (for CORS)

## Frontend Environment Variables

In `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000  # Local development
# Or for production:
# VITE_API_URL=https://your-render-app.onrender.com
```
