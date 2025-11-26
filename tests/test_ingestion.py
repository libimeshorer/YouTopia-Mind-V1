"""Tests for ingestion pipeline"""

import pytest

from src.ingestion.chunking import TextChunker


@pytest.fixture
def text_chunker():
    """Create a test text chunker"""
    return TextChunker(chunk_size=100, chunk_overlap=20)


def test_text_chunker(text_chunker):
    """Test text chunking"""
    text = "This is a test document. " * 20  # Long text
    chunks = text_chunker.chunk_text(text)
    
    assert len(chunks) > 1
    assert all("text" in chunk for chunk in chunks)
    assert all("metadata" in chunk for chunk in chunks)


def test_chunk_by_sentences(text_chunker):
    """Test sentence-based chunking"""
    text = "First sentence. Second sentence. Third sentence. " * 10
    chunks = text_chunker.chunk_by_sentences(text)
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)


