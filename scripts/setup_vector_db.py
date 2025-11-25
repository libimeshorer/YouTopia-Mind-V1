"""Script to initialize vector database"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.rag.vector_store import VectorStore
from src.utils.logging import configure_logging, get_logger
from src.config.settings import settings

configure_logging(settings.log_level)
logger = get_logger(__name__)


def main():
    """Initialize vector database"""
    logger.info("Initializing vector database", db_path=settings.chroma_db_path)
    
    vector_store = VectorStore()
    
    count = vector_store.get_collection_count()
    logger.info("Vector database initialized", document_count=count)
    
    print(f"Vector database initialized with {count} documents")


if __name__ == "__main__":
    main()

