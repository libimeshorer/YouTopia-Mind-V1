"""FastAPI dependencies for authentication and database"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError, jwk
import requests
from typing import Optional
from dataclasses import dataclass
from uuid import UUID
from src.database.db import get_db
from src.database.models import Tenant, Clone
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
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_SECRET_KEY or CLERK_FRONTEND_API must be configured. Please set CLERK_FRONTEND_API environment variable."
        )
    
    # Safe to access clerk_secret_key now since we checked it's not None
    if "_" in settings.clerk_secret_key:
        clerk_key_type = settings.clerk_secret_key.split("_")[1]
    else:
        clerk_key_type = "clerk"
    
    # Note: This fallback URL format is incorrect and should not be used in production
    # It's kept as a last resort fallback, but CLERK_FRONTEND_API should always be set
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


@dataclass
class CloneContext:
    """Context object containing clone and tenant information"""
    clone_id: UUID
    tenant_id: UUID
    clone: Clone


def get_clone_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> CloneContext:
    """
    FastAPI dependency to get the current authenticated clone context.
    Verifies Clerk JWT token, creates/looks up Tenant and Clone, returns CloneContext.
    
    Initial Implementation (Solopreneurs - 1:1 Clone-to-Tenant):
    - Each clone gets their own tenant_id (1:1 relationship)
    - When a clone signs up, automatically create a new Tenant record for them
    - This supports solopreneurs who are the only clone in their company
    
    TODO: Update this logic when onboarding bigger companies with multiple clones per tenant
    - Extract org_id from Clerk JWT token org_id claim
    - Update the org name in the Tenant model, replacing the general name generated by the system
    - Group multiple clones under the same tenant_id based on organization
    - Create tenant management/admin flow for assigning clones to existing tenants
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
    
    # Extract org info from JWT
    org_info = payload.get("org", {})
    org_id = org_info.get("id") if org_info else None
    org_name = org_info.get("name", "") if org_info else ""
    
    # Extract user info from JWT
    first_name = payload.get("first_name") or payload.get("given_name")
    last_name = payload.get("last_name") or payload.get("family_name")
    email = payload.get("email")
    
    # Get or create Clone first
    clone = db.query(Clone).filter(Clone.clerk_user_id == clerk_user_id).first()
    
    if clone:
        # Clone exists, use its tenant_id
        tenant = db.query(Tenant).filter(Tenant.id == clone.tenant_id).first()
        if not tenant:
            # Safety check: tenant should always exist
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Clone has invalid tenant_id"
            )
        
        # Update clone info if available (in case JWT has updated info)
        if first_name and clone.first_name != first_name:
            clone.first_name = first_name
        if last_name and clone.last_name != last_name:
            clone.last_name = last_name
        if email and clone.email != email:
            clone.email = email
        if clone.first_name or clone.last_name or clone.email:
            db.commit()
    else:
        # New clone signup - create tenant and clone
        # Find or create tenant based on org_id
        if org_id:
            # Enterprise: find existing tenant by org_id
            tenant = db.query(Tenant).filter(Tenant.clerk_org_id == org_id).first()
            if not tenant:
                tenant = Tenant(
                    name=org_name or f"Organization {org_id[:8]}",
                    clerk_org_id=org_id
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
        else:
            # Solopreneur: create personal tenant
            user_name = f"{first_name or ''} {last_name or ''}".strip() or f"User {clerk_user_id[:8]}"
            tenant = Tenant(
                name=f"Personal workspace for {user_name}",
                clerk_org_id=None
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
        
        # Create clone linked to tenant
        clone = Clone(
            tenant_id=tenant.id,
            clerk_user_id=clerk_user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            status="active"
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        logger.info("Created new clone with tenant", clone_id=str(clone.id), tenant_id=str(tenant.id), org_id=org_id)
    
    return CloneContext(clone_id=clone.id, tenant_id=tenant.id, clone=clone)


# DEPRECATED: get_current_user() removed - User model no longer exists
# Use get_clone_context() instead
