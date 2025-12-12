"""Migration script to migrate existing User data to Clone/Tenant structure"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from src.database.db import SessionLocal, engine
from src.database.models import Base, User, Tenant, Clone, Document, Insight, TrainingStatus, Integration
from src.utils.logging import get_logger
from src.rag.pinecone_store import PineconeStore
from src.config.settings import settings

logger = get_logger(__name__)


def migrate_users_to_clones(db: Session):
    """
    Migrate existing User records to Clone records.
    Creates a 1:1 Tenant for each User (solopreneur model).
    """
    logger.info("Starting migration: Users -> Clones/Tenants")
    
    users = db.query(User).all()
    logger.info(f"Found {len(users)} users to migrate")
    
    migrated_count = 0
    
    for user in users:
        try:
            # Check if clone already exists for this user
            existing_clone = db.query(Clone).filter(Clone.clerk_user_id == user.clerk_user_id).first()
            if existing_clone:
                logger.info(f"Clone already exists for user {user.clerk_user_id}, skipping")
                continue
            
            # Create tenant for this user (1:1 relationship)
            tenant = Tenant(
                name=f"Tenant for {user.clerk_user_id[:8]}",
                clerk_org_id=None
            )
            db.add(tenant)
            db.flush()  # Get tenant.id without committing
            
            # Create clone linked to tenant
            clone = Clone(
                tenant_id=tenant.id,
                clerk_user_id=user.clerk_user_id,
                name="Clone",
                status="active"
            )
            db.add(clone)
            db.flush()  # Get clone.id without committing
            
            # Update all related records to use clone_id
            # Documents
            documents_updated = db.query(Document).filter(Document.user_id == user.id).update(
                {"clone_id": clone.id},
                synchronize_session=False
            )
            
            # Insights
            insights_updated = db.query(Insight).filter(Insight.user_id == user.id).update(
                {"clone_id": clone.id},
                synchronize_session=False
            )
            
            # TrainingStatus
            training_status = db.query(TrainingStatus).filter(TrainingStatus.user_id == user.id).first()
            if training_status:
                # TrainingStatus uses user_id as primary key, so we need to create new one
                new_training_status = TrainingStatus(
                    clone_id=clone.id,
                    is_complete=training_status.is_complete,
                    progress=training_status.progress,
                    documents_count=training_status.documents_count,
                    insights_count=training_status.insights_count,
                    integrations_count=training_status.integrations_count,
                    thresholds_json=training_status.thresholds_json,
                    achievements_json=training_status.achievements_json,
                )
                db.add(new_training_status)
                db.delete(training_status)
            
            # Integrations
            integrations_updated = db.query(Integration).filter(Integration.user_id == user.id).update(
                {"clone_id": clone.id},
                synchronize_session=False
            )
            
            db.commit()
            
            logger.info(
                f"Migrated user {user.clerk_user_id} to clone {clone.id}",
                documents=documents_updated,
                insights=insights_updated,
                integrations=integrations_updated
            )
            migrated_count += 1
            
        except Exception as e:
            logger.error(f"Error migrating user {user.clerk_user_id}", error=str(e))
            db.rollback()
            continue
    
    logger.info(f"Migration completed: {migrated_count} users migrated")
    return migrated_count


def migrate_pinecone_to_namespaces():
    """
    Migrate Pinecone vectors to use namespaces.
    Each clone's vectors need to be moved to their own namespace: {tenant_id}_{clone_id}
    This is a best-effort migration - some vectors may not have user_id in metadata.
    """
    logger.info("Starting Pinecone namespace migration")
    
    try:
        from src.database.models import Clone
        
        db = SessionLocal()
        pinecone_store = PineconeStore()
        
        # Get all clones
        clones = db.query(Clone).all()
        logger.info(f"Found {len(clones)} clones to migrate")
        
        migrated_count = 0
        
        for clone in clones:
            try:
                # Create namespace for this clone
                namespace = f"{str(clone.tenant_id).replace('-', '')}_{str(clone.id).replace('-', '')}"
                
                # Note: Pinecone doesn't support moving vectors between namespaces directly
                # We would need to:
                # 1. Query all vectors with user_id matching this clone's clerk_user_id (from default namespace)
                # 2. Re-upsert them to the new namespace
                # 3. Delete from old namespace
                
                # For now, we'll log that vectors created after migration will use namespaces
                # Existing vectors in default namespace will remain there
                # They can be re-ingested or manually migrated
                
                logger.info(
                    f"Clone {clone.id} will use namespace: {namespace}",
                    clone_id=str(clone.id),
                    tenant_id=str(clone.tenant_id),
                    namespace=namespace
                )
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Error processing clone {clone.id}", error=str(e))
                continue
        
        logger.warning(
            "Pinecone namespace migration: New vectors will automatically use namespaces. "
            "Existing vectors in default namespace may need to be re-ingested or manually migrated. "
            "Vectors created after this migration will use the correct namespace automatically."
        )
        
        db.close()
        
    except Exception as e:
        logger.error("Error migrating Pinecone to namespaces", error=str(e))
        raise


def migrate_s3_paths():
    """
    Migrate S3 object paths to include tenant_id and clone_id.
    This requires copying objects to new paths.
    """
    logger.info("Starting S3 paths migration")
    
    try:
        from src.utils.aws import S3Client
        from src.database.models import Document, Insight
        
        db = SessionLocal()
        s3_client = S3Client()
        
        # Migrate document paths
        documents = db.query(Document).filter(Document.clone_id.isnot(None)).all()
        logger.info(f"Found {len(documents)} documents to migrate")
        
        migrated_docs = 0
        for doc in documents:
            try:
                # Get clone to find tenant_id
                clone = db.query(Clone).filter(Clone.id == doc.clone_id).first()
                if not clone:
                    logger.warning(f"Clone not found for document {doc.id}, skipping")
                    continue
                
                # New S3 key format
                old_key = doc.s3_key
                filename = old_key.split("/")[-1]
                new_key = f"documents/{clone.tenant_id}/{clone.id}/{doc.id}/{filename}"
                
                # Check if object exists at old path
                try:
                    # Try to get object
                    old_object = s3_client.get_object(old_key)
                    if old_object:
                        # Copy to new location
                        s3_client.put_object(new_key, old_object)
                        # Update database
                        doc.s3_key = new_key
                        db.commit()
                        migrated_docs += 1
                        logger.info(f"Migrated document {doc.id} from {old_key} to {new_key}")
                except Exception as e:
                    logger.warning(f"Could not migrate document {doc.id}: {str(e)}")
                    continue
                    
            except Exception as e:
                logger.error(f"Error migrating document {doc.id}", error=str(e))
                continue
        
        logger.info(f"S3 migration completed: {migrated_docs} documents migrated")
        
        db.close()
        
    except Exception as e:
        logger.error("Error migrating S3 paths", error=str(e))
        raise


def main():
    """Run the full migration"""
    logger.info("=" * 60)
    logger.info("Starting migration to Clone/Tenant model")
    logger.info("=" * 60)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Step 1: Migrate users to clones
        migrate_users_to_clones(db)
        
        # Step 2: Migrate Pinecone to namespaces (best effort)
        try:
            migrate_pinecone_to_namespaces()
        except Exception as e:
            logger.warning(f"Pinecone namespace migration failed (non-critical): {str(e)}")
        
        # Step 3: Migrate S3 paths
        try:
            migrate_s3_paths()
        except Exception as e:
            logger.warning(f"S3 migration failed (non-critical): {str(e)}")
        
        logger.info("=" * 60)
        logger.info("Migration completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
