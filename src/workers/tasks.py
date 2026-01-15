"""Celery tasks for agent observation and classification"""

import logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


def _update_capability_status_to_error(db, capability_id: str, error_message: str):
    """Helper to update AgentCapability status to 'error' after final failure."""
    try:
        from src.database.models import AgentCapability
        capability = db.query(AgentCapability).filter(
            AgentCapability.id == capability_id
        ).first()
        if capability:
            capability.status = "error"
            capability.error_message = error_message[:500]  # Truncate if too long
            db.commit()
            logger.info(f"Updated capability {capability_id} status to 'error'")
    except Exception as e:
        logger.error(f"Failed to update capability status: {e}")
        db.rollback()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def observe_all_clones(self):
    """
    Periodic task: Trigger observation for all clones with active observer capabilities.
    Runs every 4 hours via Celery Beat.
    """
    from src.database.db import SessionLocal
    from src.agents.orchestrator import AgentOrchestrator

    task_id = self.request.id
    logger.info(f"[task_id={task_id}] Starting observation run for all clones")

    try:
        db = SessionLocal()
        try:
            orchestrator = AgentOrchestrator(db)
            results = orchestrator.run_all_observations()
            logger.info(f"[task_id={task_id}] Observation run complete: {results}")
            return results
        finally:
            db.close()

    except SoftTimeLimitExceeded:
        logger.error(f"[task_id={task_id}] Observation task hit soft time limit")
        raise
    except Exception as e:
        logger.warning(
            f"[task_id={task_id}] Observation task failed (attempt {self.request.retries + 1}/{self.max_retries + 1}): {e}"
        )
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(
                f"[task_id={task_id}] Observation task failed permanently after {self.max_retries + 1} attempts: {e}"
            )
            # Return error info instead of raising - allows task to complete with failure info
            return {"status": "failed", "error": str(e), "task_id": task_id}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def observe_and_classify_for_clone(self, clone_id: str, capability_id: str):
    """
    Task: Run observation and classification for a single clone.
    Can be triggered manually or by observe_all_clones.
    """
    from src.database.db import SessionLocal
    from src.agents.orchestrator import AgentOrchestrator

    task_id = self.request.id
    logger.info(f"[task_id={task_id}] Starting observation for clone {clone_id}, capability {capability_id}")

    db = None
    try:
        db = SessionLocal()
        orchestrator = AgentOrchestrator(db)
        result = orchestrator.run_observation_for_clone(clone_id, capability_id)
        logger.info(f"[task_id={task_id}] Observation complete for clone {clone_id}: {result}")
        return result

    except SoftTimeLimitExceeded:
        logger.error(f"[task_id={task_id}] Observation task for clone {clone_id} hit soft time limit")
        if db and capability_id:
            _update_capability_status_to_error(
                db, capability_id, "Task exceeded time limit"
            )
        raise
    except Exception as e:
        logger.warning(
            f"[task_id={task_id}] Observation task for clone {clone_id} failed "
            f"(attempt {self.request.retries + 1}/{self.max_retries + 1}): {e}"
        )
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(
                f"[task_id={task_id}] Observation task for clone {clone_id} failed permanently "
                f"after {self.max_retries + 1} attempts: {e}"
            )
            # Update capability status to error so user sees the issue
            if db and capability_id:
                _update_capability_status_to_error(db, capability_id, str(e))
            # Return error info instead of raising
            return {
                "status": "failed",
                "error": str(e),
                "clone_id": clone_id,
                "capability_id": capability_id,
                "task_id": task_id,
            }
    finally:
        if db:
            db.close()
