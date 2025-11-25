# Deployment Guide

## AWS Lambda Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. S3 bucket created for data storage
3. Secrets Manager secret created (optional, can use environment variables)

### Step 1: Create S3 Bucket

```bash
aws s3 mb s3://youtopia-mind-data --region us-east-1
```

### Step 2: Create Secrets in Secrets Manager (Optional)

```bash
aws secretsmanager create-secret \
  --name youtopia-mind-secrets \
  --secret-string '{
    "SLACK_BOT_TOKEN": "xoxb-your-token",
    "SLACK_SIGNING_SECRET": "your-secret",
    "OPENAI_API_KEY": "sk-your-key",
    "S3_BUCKET_NAME": "youtopia-mind-data"
  }' \
  --region us-east-1
```

### Step 3: Package Lambda Function

```bash
# Create deployment package
zip -r lambda-deployment.zip . \
  -x "*.git*" \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x "venv/*" \
  -x "data/*" \
  -x "test_data/*" \
  -x "*.md" \
  -x ".env*"
```

### Step 4: Create Lambda Function

```bash
aws lambda create-function \
  --function-name youtopia-mind-slack-bot \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler deployment.lambda_function.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables="{
    S3_BUCKET_NAME=youtopia-mind-data,
    AWS_REGION=us-east-1,
    LOG_LEVEL=INFO
  }"
```

### Step 5: Configure Slack Events API

1. In Slack API dashboard, set Request URL to:
   ```
   https://YOUR_API_GATEWAY_URL/slack/events
   ```

2. Subscribe to events:
   - `app_mention`
   - `message.im`
   - `app_home_opened`

### Step 6: Set Up API Gateway (if needed)

```bash
# Create API Gateway REST API
aws apigateway create-rest-api --name youtopia-mind-api

# Follow AWS documentation to connect API Gateway to Lambda
```

## Local Development Setup

### Using Socket Mode

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables in `.env`:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...
OPENAI_API_KEY=sk-...
S3_BUCKET_NAME=youtopia-mind-data
```

3. Run the bot:
```bash
python src/bot/slack_handler.py
```

## Initial Data Ingestion

Before the bot can respond effectively, ingest data:

```bash
# Ingest documents
python scripts/ingest_data.py --documents doc1.pdf doc2.docx

# Ingest Slack history
python scripts/ingest_data.py --slack-channel C1234567890 --limit 1000

# This will:
# 1. Extract and chunk text
# 2. Generate embeddings
# 3. Store in vector database
# 4. Analyze personality/style
# 5. Save profile to S3
```

## Monitoring

### CloudWatch Logs

Lambda logs are automatically sent to CloudWatch. Monitor:
- Function errors
- Response times
- Token usage (for cost tracking)

### Cost Monitoring

Set up AWS Cost Alerts:
```bash
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json
```

## Troubleshooting

### Lambda Timeout

If Lambda times out:
- Increase timeout in Lambda configuration
- Optimize RAG retrieval (reduce top_k)
- Use streaming responses

### Memory Issues

If out of memory:
- Increase Lambda memory allocation
- Optimize chunk sizes
- Reduce context window

### ChromaDB in Lambda

For Lambda, consider:
- Using S3-backed ChromaDB
- Or migrating to managed vector DB (Pinecone)

## Production Checklist

- [ ] Environment variables configured
- [ ] S3 bucket created and accessible
- [ ] Secrets Manager configured (if using)
- [ ] Lambda function deployed
- [ ] API Gateway configured
- [ ] Slack Events API configured
- [ ] Initial data ingested
- [ ] Personality profile generated
- [ ] CloudWatch alarms set up
- [ ] Cost monitoring enabled
- [ ] Error handling tested
- [ ] Rate limiting configured


