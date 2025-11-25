"""CLI script for incremental data ingestion (new uploads)"""

import sys
import argparse
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.ingestion.pipeline import IngestionPipeline
from src.personality.style_analyzer import StyleAnalyzer
from src.utils.logging import configure_logging, get_logger
from src.config.settings import settings

configure_logging(settings.log_level)
logger = get_logger(__name__)


def main():
    """Main incremental ingestion script"""
    parser = argparse.ArgumentParser(description="Ingest new data for digital twin")
    parser.add_argument("--document", required=True, help="New document file path to ingest")
    parser.add_argument("--source-name", help="Source name for the document")
    parser.add_argument("--update-profile", action="store_true", help="Update personality profile with new data")
    
    args = parser.parse_args()
    
    # Initialize components
    pipeline = IngestionPipeline()
    style_analyzer = StyleAnalyzer()
    
    # Load existing profile
    profile = style_analyzer.load_profile()
    
    # Ingest new document
    logger.info("Ingesting new document", file_path=args.document)
    chunk_count = pipeline.ingest_new_document(args.document, source_name=args.source_name)
    
    logger.info("New document ingested", chunk_count=chunk_count)
    
    # Update personality profile if requested
    if args.update_profile:
        logger.info("Updating personality profile")
        try:
            from src.ingestion.document_ingester import DocumentIngester
            ingester = DocumentIngester()
            text = ingester.extract_text(args.document)
            
            if profile:
                style_analyzer.update_profile_from_new_data([text])
            else:
                style_analyzer.analyze_texts([text])
            
            style_analyzer.save_profile()
            logger.info("Personality profile updated")
        except Exception as e:
            logger.warning("Could not update personality profile", error=str(e))
    
    logger.info("Incremental ingestion completed")


if __name__ == "__main__":
    main()

