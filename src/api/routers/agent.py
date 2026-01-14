"""Agent API router - capabilities, digest, and feedback endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

from src.api.dependencies import get_clone_context, CloneContext, get_db
from src.database.models import AgentCapability, AgentPreference, Integration
from src.agents.orchestrator import AgentOrchestrator
from src.agents.digest.service import DigestService
from src.agents.feedback.service import FeedbackService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ChannelConfig(BaseModel):
    id: str
    name: str


class PreferenceSetup(BaseModel):
    description: str
    keywords: List[str] = []
    example: Optional[dict] = None  # {text, explanation}


class SlackSetupRequest(BaseModel):
    integrationId: str = Field(..., description="ID of the connected Slack integration")
    channels: List[ChannelConfig]
    preferences: dict[str, PreferenceSetup]  # very_interesting, interesting, not_interesting


class CapabilityResponse(BaseModel):
    id: str
    platform: str
    capabilityType: str
    status: str
    config: dict
    lastRunAt: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: str


class ObservationResponse(BaseModel):
    id: str
    content: str
    sourceMetadata: dict
    classification: Optional[str]
    classificationConfidence: Optional[float]
    classificationReasoning: Optional[str]
    needsReview: bool
    userFeedback: Optional[str]
    status: str
    observedAt: str
    createdAt: str


class DigestStatsResponse(BaseModel):
    totalObservations: int
    pendingReview: int
    veryInterestingCount: int
    interestingCount: int
    interestingShown: int
    reviewNeededCount: int
    lastObservationAt: Optional[str]
    periodDays: int


class DigestResponse(BaseModel):
    veryInteresting: List[ObservationResponse]
    interesting: List[ObservationResponse]
    reviewNeeded: List[ObservationResponse]
    notInterestingSample: List[ObservationResponse]
    stats: DigestStatsResponse


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., description="confirmed or corrected_to_{category}")
    comment: Optional[str] = None


class AddExampleRequest(BaseModel):
    text: str
    explanation: str


class UpdatePreferenceRequest(BaseModel):
    description: str
    keywords: Optional[List[str]] = None


class PreferenceResponse(BaseModel):
    id: str
    preferenceType: str
    platform: Optional[str]
    description: Optional[str]
    keywords: List[str]
    examplesCount: int


# =============================================================================
# Capability Endpoints
# =============================================================================

@router.get("/agent/capabilities", response_model=List[CapabilityResponse])
async def list_capabilities(
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all agent capabilities for the current clone"""
    try:
        capabilities = (
            db.query(AgentCapability)
            .filter(AgentCapability.clone_id == clone_context.clone_id)
            .all()
        )

        return [
            CapabilityResponse(
                id=str(cap.id),
                platform=cap.platform,
                capabilityType=cap.capability_type,
                status=cap.status.value if hasattr(cap.status, 'value') else str(cap.status),
                config=cap.config or {},
                lastRunAt=cap.last_run_at.isoformat() if cap.last_run_at else None,
                errorMessage=cap.error_message,
                createdAt=cap.created_at.isoformat(),
            )
            for cap in capabilities
        ]
    except Exception as e:
        logger.error("Error listing capabilities", error=str(e), clone_id=clone_context.clone_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list capabilities"
        )


@router.post("/agent/capabilities/slack/setup", response_model=CapabilityResponse)
async def setup_slack_capability(
    request: SlackSetupRequest,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Set up Slack observer capability"""
    try:
        # Verify integration exists and is connected
        integration = (
            db.query(Integration)
            .filter(Integration.id == request.integrationId)
            .filter(Integration.clone_id == clone_context.clone_id)
            .first()
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        if integration.status != "connected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integration not connected: {integration.status}"
            )

        # Check if capability already exists
        existing = (
            db.query(AgentCapability)
            .filter(AgentCapability.clone_id == clone_context.clone_id)
            .filter(AgentCapability.platform == "slack")
            .filter(AgentCapability.capability_type == "observer")
            .first()
        )

        if existing:
            # Update existing capability
            existing.config = {
                "channels": [{"id": c.id, "name": c.name} for c in request.channels],
                "frequency_minutes": 240,
            }
            existing.integration_id = UUID(request.integrationId)
            existing.status = "active"
            existing.error_message = None
            capability = existing
        else:
            # Create new capability
            orchestrator = AgentOrchestrator(db)
            capability = orchestrator.create_capability(
                clone_id=clone_context.clone_id,
                platform="slack",
                capability_type="observer",
                config={
                    "channels": [{"id": c.id, "name": c.name} for c in request.channels],
                    "frequency_minutes": 240,
                },
                integration_id=UUID(request.integrationId),
            )

        # Set up preferences
        feedback_service = FeedbackService(db)
        for pref_type, pref_data in request.preferences.items():
            feedback_service.update_preference_description(
                clone_id=clone_context.clone_id,
                category=pref_type,
                description=pref_data.description,
                keywords=pref_data.keywords,
            )

            # Add example if provided
            if pref_data.example:
                feedback_service.add_manual_example(
                    clone_id=clone_context.clone_id,
                    category=pref_type,
                    text=pref_data.example.get("text", ""),
                    explanation=pref_data.example.get("explanation", ""),
                )

        db.commit()

        return CapabilityResponse(
            id=str(capability.id),
            platform=capability.platform,
            capabilityType=capability.capability_type,
            status=capability.status.value if hasattr(capability.status, 'value') else str(capability.status),
            config=capability.config or {},
            lastRunAt=capability.last_run_at.isoformat() if capability.last_run_at else None,
            errorMessage=capability.error_message,
            createdAt=capability.created_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error setting up Slack capability", error=str(e), clone_id=clone_context.clone_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up Slack capability"
        )


@router.patch("/agent/capabilities/{capability_id}")
async def update_capability(
    capability_id: str,
    config: dict,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Update capability configuration"""
    try:
        capability = (
            db.query(AgentCapability)
            .filter(AgentCapability.id == capability_id)
            .filter(AgentCapability.clone_id == clone_context.clone_id)
            .first()
        )

        if not capability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability not found"
            )

        # Update config (merge with existing)
        existing_config = capability.config or {}
        existing_config.update(config)
        capability.config = existing_config

        db.commit()

        return {"success": True, "id": capability_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating capability", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update capability"
        )


@router.delete("/agent/capabilities/{capability_id}")
async def delete_capability(
    capability_id: str,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Delete a capability"""
    try:
        capability = (
            db.query(AgentCapability)
            .filter(AgentCapability.id == capability_id)
            .filter(AgentCapability.clone_id == clone_context.clone_id)
            .first()
        )

        if not capability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability not found"
            )

        db.delete(capability)
        db.commit()

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting capability", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete capability"
        )


# =============================================================================
# Digest Endpoints
# =============================================================================

@router.get("/agent/digest", response_model=DigestResponse)
async def get_digest(
    days: int = 7,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Get the current digest of observations"""
    try:
        service = DigestService(db)
        digest = service.generate_digest(clone_context.clone_id, days=days)

        return DigestResponse(
            veryInteresting=[_format_observation(o) for o in digest["very_interesting"]],
            interesting=[_format_observation(o) for o in digest["interesting"]],
            reviewNeeded=[_format_observation(o) for o in digest["review_needed"]],
            notInterestingSample=[_format_observation(o) for o in digest["not_interesting_sample"]],
            stats=DigestStatsResponse(
                totalObservations=digest["stats"]["total_observations"],
                pendingReview=digest["stats"]["pending_review"],
                veryInterestingCount=digest["stats"]["very_interesting_count"],
                interestingCount=digest["stats"]["interesting_count"],
                interestingShown=digest["stats"]["interesting_shown"],
                reviewNeededCount=digest["stats"]["review_needed_count"],
                lastObservationAt=digest["stats"]["last_observation_at"],
                periodDays=digest["stats"]["period_days"],
            ),
        )

    except Exception as e:
        logger.error("Error generating digest", error=str(e), clone_id=clone_context.clone_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate digest"
        )


def _format_observation(obs: dict) -> ObservationResponse:
    """Format observation dict for API response"""
    return ObservationResponse(
        id=obs["id"],
        content=obs["content"],
        sourceMetadata=obs["source_metadata"],
        classification=obs["classification"],
        classificationConfidence=obs["classification_confidence"],
        classificationReasoning=obs["classification_reasoning"],
        needsReview=obs["needs_review"],
        userFeedback=obs["user_feedback"],
        status=obs["status"],
        observedAt=obs["observed_at"],
        createdAt=obs["created_at"],
    )


# =============================================================================
# Feedback Endpoints
# =============================================================================

@router.post("/agent/observations/{observation_id}/feedback")
async def submit_feedback(
    observation_id: str,
    request: FeedbackRequest,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Submit feedback on an observation"""
    try:
        service = FeedbackService(db)
        result = service.submit_feedback(
            clone_id=clone_context.clone_id,
            observation_id=UUID(observation_id),
            feedback=request.feedback,
            comment=request.comment,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error submitting feedback", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


# =============================================================================
# Preference Endpoints
# =============================================================================

@router.get("/agent/preferences", response_model=List[PreferenceResponse])
async def list_preferences(
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """List all preferences for the current clone"""
    try:
        service = FeedbackService(db)
        prefs = service.get_preferences(clone_context.clone_id)

        return [
            PreferenceResponse(
                id=p["id"],
                preferenceType=p["preference_type"],
                platform=p["platform"],
                description=p["description"],
                keywords=p["keywords"],
                examplesCount=p["examples_count"],
            )
            for p in prefs
        ]

    except Exception as e:
        logger.error("Error listing preferences", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list preferences"
        )


@router.post("/agent/preferences/{preference_type}/examples")
async def add_example(
    preference_type: str,
    request: AddExampleRequest,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Add an example to a preference category"""
    try:
        service = FeedbackService(db)
        result = service.add_manual_example(
            clone_id=clone_context.clone_id,
            category=preference_type,
            text=request.text,
            explanation=request.explanation,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error adding example", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add example"
        )


@router.patch("/agent/preferences/{preference_type}")
async def update_preference(
    preference_type: str,
    request: UpdatePreferenceRequest,
    clone_context: CloneContext = Depends(get_clone_context),
    db: Session = Depends(get_db)
):
    """Update a preference description and keywords"""
    try:
        service = FeedbackService(db)
        result = service.update_preference_description(
            clone_id=clone_context.clone_id,
            category=preference_type,
            description=request.description,
            keywords=request.keywords,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error updating preference", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preference"
        )
