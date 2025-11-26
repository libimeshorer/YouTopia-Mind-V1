"""Tests for RAG system"""

import pytest  # type: ignore[import-not-found]

from src.rag.vector_store import VectorStore
from src.rag.retriever import RAGRetriever


@pytest.fixture
def vector_store():
    """Create a test vector store"""
    return VectorStore(collection_name="test_collection", persist_directory="./test_data/chroma_db")


@pytest.fixture
def rag_retriever(vector_store):
    """Create a test RAG retriever"""
    return RAGRetriever(vector_store=vector_store)


def test_vector_store_add_texts(vector_store):
    """Test adding texts to vector store"""
    texts = ["This is a test document", "Another test document"]
    metadatas = [{"source": "test1"}, {"source": "test2"}]
    
    ids = vector_store.add_texts(texts, metadatas=metadatas)
    assert len(ids) == 2


def test_vector_store_search(vector_store):
    """Test searching vector store"""
    texts = ["Python programming language", "Machine learning algorithms"]
    vector_store.add_texts(texts)
    
    results = vector_store.search("programming", n_results=1)
    assert len(results) > 0
    assert "Python" in results[0]["text"]


def test_rag_retriever(rag_retriever):
    """Test RAG retriever"""
    texts = ["Artificial intelligence", "Natural language processing"]
    rag_retriever.vector_store.add_texts(texts)
    
    results = rag_retriever.retrieve("AI", top_k=1)
    assert len(results) > 0
    
    context = rag_retriever.format_context(results)
    assert len(context) > 0


