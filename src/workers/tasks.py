"""Celery tasks for agent observation and classification"""

import logging
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def observe_all_clones(self):
    """
    Periodic task: Trigger observation for all clones with active observer capabilities.
    Runs every 4 hours via Celery Beat.
    """
    from src.database.db import SessionLocal
    from src.agents.orchestrator import AgentOrchestrator

    logger.info("Starting observation run for all clones")

    try:
        db = SessionLocal()
        try:
            orchestrator = AgentOrchestrator(db)
            results = orchestrator.run_all_observations()
            logger.info(f"Observation run complete: {results}")
            return results
        finally:
            db.close()

    except SoftTimeLimitExceeded:
        logger.error("Observation task hit soft time limit")
        raise
    except Exception as e:
        logger.error(f"Observation task failed: {e}")
        self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def observe_and_classify_for_clone(self, clone_id: str, capability_id: str):
    """
    Task: Run observation and classification for a single clone.
    Can be triggered manually or by observe_all_clones.
    """
    from src.database.db import SessionLocal
    from src.agents.orchestrator import AgentOrchestrator

    logger.info(f"Starting observation for clone {clone_id}")

    try:
        db = SessionLocal()
        try:
            orchestrator = AgentOrchestrator(db)
            result = orchestrator.run_observation_for_clone(clone_id, capability_id)
            logger.info(f"Observation complete for clone {clone_id}: {result}")
            return result
        finally:
            db.close()

    except SoftTimeLimitExceeded:
        logger.error(f"Observation task for clone {clone_id} hit soft time limit")
        raise
    except Exception as e:
        logger.error(f"Observation task for clone {clone_id} failed: {e}")
        self.retry(exc=e)
