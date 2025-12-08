"""FastAPI dependencies for authentication and database"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError, jwk
import requests
from typing import Optional
from src.database.db import get_db
from src.database.models import User
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()

# Cache for Clerk JWKS
_clerk_jwks_cache = None
_clerk_jwks_url = None


def get_clerk_jwks_url() -> str:
    """Get Clerk JWKS URL from secret key or environment variable"""
    # Try to get from environment variable first
    import os
    clerk_frontend_api = os.getenv("CLERK_FRONTEND_API", "")
    
    if clerk_frontend_api:
        # If CLERK_FRONTEND_API is set, use it directly
        if clerk_frontend_api.startswith("http"):
            return f"{clerk_frontend_api}/.well-known/jwks.json"
        else:
            return f"https://{clerk_frontend_api}/.well-known/jwks.json"
    
    # Fallback: Extract from secret key (simplified approach)
    # Clerk secret keys are in format: sk_test_... or sk_live_...
    # This is a simplified approach - in production, set CLERK_FRONTEND_API env var
    clerk_key_type = settings.clerk_secret_key.split("_")[1] if "_" in settings.clerk_secret_key else "clerk"
    return f"https://clerk.{clerk_key_type}.lcl.dev/.well-known/jwks.json"


def get_clerk_jwks():
    """Fetch and cache Clerk JWKS"""
    global _clerk_jwks_cache, _clerk_jwks_url
    
    jwks_url = get_clerk_jwks_url()
    
    # Return cached if available and URL hasn't changed
    if _clerk_jwks_cache and _clerk_jwks_url == jwks_url:
        return _clerk_jwks_cache
    
    try:
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        _clerk_jwks_cache = response.json()
        _clerk_jwks_url = jwks_url
        return _clerk_jwks_cache
    except Exception as e:
        logger.error("Error fetching Clerk JWKS", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication"
        )


def verify_clerk_token(token: str) -> dict:
    """Verify Clerk JWT token and return payload"""
    try:
        # Get JWKS
        jwks = get_clerk_jwks()
        
        # Get token header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token header"
            )
        
        # Find the key in JWKS
        jwk_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                jwk_key = key
                break
        
        if not jwk_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token key ID"
            )
        
        # Construct the public key from JWK
        public_key = jwk.construct(jwk_key)
        
        # Get issuer from JWKS URL or environment
        import os
        issuer = os.getenv("CLERK_ISSUER", "")
        audience = os.getenv("CLERK_AUDIENCE", "")
        
        # Decode and verify token
        # python-jose can use the JWK dict directly or the constructed key
        # We'll use the JWK dict with the key parameter
        decode_options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_aud": bool(audience),
            "verify_iss": bool(issuer),
        }
        
        # Convert JWK to PEM format for jwt.decode
        try:
            key_pem = public_key.to_pem().decode('utf-8')
        except AttributeError:
            # If to_pem doesn't exist, try using the JWK dict directly
            key_pem = jwk_key
        
        payload = jwt.decode(
            token,
            key_pem,
            algorithms=[jwk_key.get("alg", "RS256")],
            audience=audience if audience else None,
            issuer=issuer if issuer else None,
            options=decode_options
        )
        
        return payload
    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except Exception as e:
        logger.error("Error verifying token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.
    Verifies Clerk JWT token and returns the User model.
    """
    token = credentials.credentials
    
    # Verify token
    payload = verify_clerk_token(token)
    
    # Extract user ID from token
    # Clerk tokens typically have 'sub' or 'userId' claim
    clerk_user_id = payload.get("sub") or payload.get("userId")
    
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID"
        )
    
    # Get or create user in database
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    
    if not user:
        # Create new user
        user = User(clerk_user_id=clerk_user_id)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new user", clerk_user_id=clerk_user_id, user_id=str(user.id))
    
    return user
