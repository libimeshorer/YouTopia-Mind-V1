#!/usr/bin/env python3
"""Simple compatibility test that doesn't require environment variables"""

import sys

def test_core_imports():
    """Test that core packages can be imported"""
    # Test FastAPI
    from fastapi import FastAPI
    app = FastAPI()
    assert app is not None
    
    # Test Pydantic
    from pydantic import BaseModel
    class TestModel(BaseModel):
        name: str
    test = TestModel(name="test")
    assert test.name == "test"
    
    # Test Pinecone (new package)
    from pinecone import Pinecone, ServerlessSpec
    assert Pinecone is not None
    assert ServerlessSpec is not None
    
    # Test python-jose (updated version)
    from jose import jwt
    assert jwt is not None
    
    # Test python-multipart (updated version)
    from multipart import multipart
    assert multipart is not None
    
    # Test SQLAlchemy
    from sqlalchemy import create_engine
    assert create_engine is not None
    
    # Test LangChain
    from langchain import __version__
    assert __version__ is not None
    
    # Test OpenAI
    from openai import OpenAI
    assert OpenAI is not None
    
    print("✓ All core package imports successful")
    return True

def test_package_versions():
    """Verify we have the correct updated versions"""
    import fastapi
    import pinecone
    import pydantic
    import jose
    
    print(f"✓ FastAPI: {fastapi.__version__} (>= 0.115.14)")
    print(f"✓ Pinecone: {pinecone.__version__} (>= 5.0.0)")
    print(f"✓ Pydantic: {pydantic.__version__}")
    print(f"✓ python-jose: {jose.__version__} (>= 3.4.0)")
    
    # Verify versions meet requirements
    from packaging import version
    
    assert version.parse(fastapi.__version__) >= version.parse("0.115.14"), "FastAPI version too old"
    assert version.parse(pinecone.__version__) >= version.parse("5.0.0"), "Pinecone version too old"
    assert version.parse(jose.__version__) >= version.parse("3.4.0"), "python-jose version too old"
    
    print("✓ All package versions meet requirements")
    return True

if __name__ == "__main__":
    print(f"Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("\n=== Testing Package Compatibility ===\n")
    
    try:
        test_core_imports()
        print()
        test_package_versions()
        print("\n=== All Compatibility Tests Passed! ===")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
