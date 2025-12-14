"""CLI script for initial bulk data ingestion"""

import sys
import argparse
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.slack_ingester import SlackIngester
from src.personality.style_analyzer import StyleAnalyzer
from src.utils.logging import configure_logging, get_logger
from src.config.settings import settings
from src.utils.environment import (
    get_environment,
    log_environment_info,
    validate_environment_config,
    is_production,
)

configure_logging(settings.log_level)
logger = get_logger(__name__)


def main():
    """Main ingestion script"""
    # Environment validation and logging
    env = get_environment()
    log_environment_info()
    
    # Validate configuration
    is_valid, warnings = validate_environment_config()
    
    # Production confirmation
    if is_production():
        logger.warning(
            "=" * 70,
        )
        logger.warning(
            "⚠️  PRODUCTION ENVIRONMENT DETECTED - Data Ingestion Script",
            environment=env,
            pinecone_index=settings.pinecone_index_name,
            s3_bucket=settings.s3_bucket_name,
        )
        logger.warning(
            "=" * 70,
        )
        logger.warning(
            "This script will ingest data into PRODUCTION resources."
        )
        logger.warning(
            "All operations will affect production data."
        )
        logger.warning(
            "",
        )
        
        response = input("⚠️  Continue with production ingestion? (type 'yes' to confirm): ")
        if response.lower() != "yes":
            logger.info("Ingestion cancelled by user")
            return
        logger.warning("Proceeding with production ingestion...")
    
    logger.info(
        "Starting data ingestion",
        environment=env,
        pinecone_index=settings.pinecone_index_name,
        s3_bucket=settings.s3_bucket_name,
    )
    
    parser = argparse.ArgumentParser(description="Ingest data for digital twin")
    parser.add_argument("--documents", nargs="+", help="Document file paths to ingest")
    parser.add_argument("--slack-channel", help="Slack channel ID to ingest")
    parser.add_argument("--slack-user", help="Slack user ID to ingest")
    parser.add_argument("--emails", nargs="+", help="Email file paths to ingest")
    parser.add_argument("--limit", type=int, default=1000, help="Limit for Slack messages")
    
    args = parser.parse_args()
    
    # Initialize components
    slack_ingester = SlackIngester() if (args.slack_channel or args.slack_user) else None
    pipeline = IngestionPipeline(slack_ingester=slack_ingester)
    style_analyzer = StyleAnalyzer()
    
    all_texts = []
    
    # Ingest documents
    if args.documents:
        logger.info("Ingesting documents", count=len(args.documents))
        pipeline.ingest_documents(args.documents)
        # Collect texts for personality analysis
        for doc_path in args.documents:
            try:
                from src.ingestion.document_ingester import DocumentIngester
                ingester = DocumentIngester()
                text = ingester.extract_text(doc_path)
                all_texts.append(text)
            except Exception as e:
                logger.warning("Could not extract text for analysis", file_path=doc_path, error=str(e))
    
    # Ingest Slack messages
    if args.slack_channel:
        logger.info("Ingesting Slack channel", channel_id=args.slack_channel)
        pipeline.ingest_slack_messages(channel_id=args.slack_channel, limit=args.limit)
        # Note: Would need to fetch messages again for personality analysis
        # For now, we'll analyze from vector store if needed
    
    if args.slack_user:
        logger.info("Ingesting Slack user messages", user_id=args.slack_user)
        pipeline.ingest_slack_messages(user_id=args.slack_user, limit=args.limit)
    
    # Ingest emails
    if args.emails:
        logger.info("Ingesting emails", count=len(args.emails))
        pipeline.ingest_emails(file_paths=args.emails)
        # Collect texts for personality analysis
        for email_path in args.emails:
            try:
                from src.ingestion.email_ingester import EmailIngester
                ingester = EmailIngester()
                email_data = ingester.parse_email_file(email_path)
                all_texts.append(email_data["text"])
            except Exception as e:
                logger.warning("Could not extract text for analysis", file_path=email_path, error=str(e))
    
    # Analyze personality
    if all_texts:
        logger.info("Analyzing personality", text_count=len(all_texts))
        profile = style_analyzer.analyze_texts(all_texts)
        style_analyzer.save_profile()
        logger.info("Personality profile created and saved")
    
    logger.info("Data ingestion completed")


if __name__ == "__main__":
    main()


