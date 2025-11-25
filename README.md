# YouTopia Mind V1 - Digital Twin Slack Bot

A production-ready digital twin (AI clone) Slack bot that uses RAG (Retrieval Augmented Generation) and GPT-4 to replicate a professional's communication style, knowledge, and decision-making patterns.

## Features

- **RAG System**: Vector-based retrieval using ChromaDB and OpenAI embeddings
- **Multi-Source Ingestion**: Supports Slack messages, emails, and documents (PDF, DOCX, TXT)
- **Personality Learning**: Automatically extracts communication style and personality traits
- **Slack Integration**: Responds to mentions and direct messages
- **AWS Deployment**: Ready for Lambda deployment with S3 and Secrets Manager
- **Incremental Updates**: Support for adding new data without full re-ingestion

## Architecture

```
┌─────────────┐
│  Slack Bot  │
└──────┬──────┘
       │
┌──────▼──────────┐
│ Message Handler │
└──────┬──────────┘
       │
┌──────▼─────────────┐     ┌──────────────┐
│  Prompt Builder    │────▶│  GPT-4 API   │
└──────┬─────────────┘     └──────────────┘
       │
       ├──────────────┐
       │              │
┌──────▼──────┐  ┌───▼──────────────┐
│ RAG Retriever│  │ Personality      │
└──────┬───────┘  │ Profile          │
       │          └──────────────────┘
┌──────▼───────┐
│ Vector Store │
│ (ChromaDB)   │
└──────────────┘
```

## Setup

### Prerequisites

- Python 3.9+
- AWS Account (for deployment)
- Slack App credentials
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd YouTopia-Mind-V1
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_SIGNING_SECRET`: Your Slack signing secret
- `SLACK_APP_TOKEN`: Your Slack app token (for socket mode)
- `OPENAI_API_KEY`: Your OpenAI API key
- `S3_BUCKET_NAME`: AWS S3 bucket name for data storage
- `AWS_REGION`: AWS region (default: us-east-1)

## Usage

### Initial Data Ingestion

Ingest data from multiple sources to build the digital twin:

```bash
# Ingest documents
python scripts/ingest_data.py --documents doc1.pdf doc2.docx

# Ingest Slack messages from a channel
python scripts/ingest_data.py --slack-channel C1234567890 --limit 1000

# Ingest Slack messages from a user
python scripts/ingest_data.py --slack-user U1234567890 --limit 1000

# Ingest emails
python scripts/ingest_data.py --emails email1.eml email2.eml

# Combine multiple sources
python scripts/ingest_data.py \
  --documents doc1.pdf doc2.docx \
  --slack-channel C1234567890 \
  --emails email1.eml
```

### Incremental Data Ingestion

Add new documents without re-ingesting everything:

```bash
python scripts/ingest_new_data.py --document new_doc.pdf --update-profile
```

### Running the Slack Bot

#### Local Development (Socket Mode)

```bash
python src/bot/slack_handler.py
```

#### AWS Lambda Deployment

1. Package the application:
```bash
zip -r lambda-deployment.zip . -x "*.git*" "*.pyc" "__pycache__/*" "venv/*" "data/*"
```

2. Deploy to Lambda using AWS CLI or Serverless Framework

3. Configure Lambda environment variables and set up API Gateway or Slack Events API

### Initialize Vector Database

```bash
python scripts/setup_vector_db.py
```

## Project Structure

```
youtopia-mind-v1/
├── src/
│   ├── bot/              # Slack bot handlers
│   ├── rag/              # RAG system (vector store, retriever)
│   ├── ingestion/        # Data ingestion pipeline
│   ├── personality/      # Style analyzer and profile
│   ├── llm/              # LLM client and prompt builder
│   ├── config/           # Configuration management
│   └── utils/            # Utilities (logging, AWS)
├── scripts/              # CLI scripts
├── deployment/           # AWS Lambda deployment files
└── tests/                # Unit and integration tests
```

## Configuration

### RAG Settings

- `CHUNK_SIZE`: Text chunk size (default: 1000)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 200)
- `TOP_K_RETRIEVAL`: Number of retrieved contexts (default: 5)
- `MAX_CONTEXT_TOKENS`: Maximum context tokens (default: 4000)

### LLM Settings

- `OPENAI_MODEL`: GPT model to use (default: gpt-4-turbo-preview)
- `OPENAI_EMBEDDING_MODEL`: Embedding model (default: text-embedding-3-small)

## AWS Deployment

### S3 Bucket Structure

```
s3://your-bucket/
├── raw/
│   ├── slack/
│   ├── emails/
│   └── documents/
├── processed/
└── profiles/
    └── personality_profile.json
```

### Lambda Configuration

- Runtime: Python 3.9+
- Handler: `deployment.lambda_function.lambda_handler`
- Timeout: 30 seconds (adjust based on needs)
- Memory: 512 MB (minimum recommended)

### Secrets Management

Store sensitive credentials in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name youtopia-mind-secrets \
  --secret-string '{"SLACK_BOT_TOKEN":"...","OPENAI_API_KEY":"..."}'
```

## Cost Estimates

**Monthly Costs (MVP - 100 interactions/day):**
- OpenAI API: ~$75-105
- AWS: ~$7-25
- **Total: ~$82-130/month**

See the plan document for detailed cost breakdown.

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 style guidelines. Consider using `black` for formatting:

```bash
black src/ scripts/
```

## Troubleshooting

### Common Issues

1. **ChromaDB errors**: Ensure the data directory exists and has write permissions
2. **Slack API errors**: Verify bot token and permissions
3. **OpenAI API errors**: Check API key and rate limits
4. **AWS errors**: Verify credentials and S3 bucket permissions

### Logging

Logs are structured and can be viewed in CloudWatch (AWS) or console (local). Set `LOG_LEVEL` environment variable to control verbosity.

## Future Enhancements

- Frontend/UI for file uploads and management
- Interviewing agent for initial data collection
- Advanced personality analysis
- Multi-person support
- Response caching
- Analytics dashboard

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository.
