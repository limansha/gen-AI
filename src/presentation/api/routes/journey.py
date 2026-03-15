import logging
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.application.journey.journey_service import JourneyService
from src.domain.entities.journey import Action
from src.infrastructure.database.connection import get_db
from src.presentation.api.dependencies import get_current_user
from src.domain.entities.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/journey", tags=["journey"])


class JourneySummaryRequest(BaseModel):
    journeySummary: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="The summary of the journey the user wants to complete",
    )


class ActionStepResponse(BaseModel):
    step: str = Field(..., description="A single step or instruction for the action")


class ActionResponse(BaseModel):
    title: str = Field(..., description="Title of the action/task")
    duration: str = Field(..., description="Estimated duration (e.g., '3–5 min')")
    steps: list[str] = Field(..., description="List of steps or instructions for the action")
    order: int = Field(..., description="Order/sequence of the action in the journey")


class JourneyActionsResponse(BaseModel):
    actions: list[ActionResponse] = Field(..., description="List of actions/tasks for the journey")


def _action_to_response(action: Action) -> ActionResponse:
    """Convert domain Action entity to API response model."""
    return ActionResponse(
        title=action.title,
        duration=action.duration,
        steps=action.steps,
        order=action.order,
    )


@router.post(
    "/actions",
    response_model=JourneyActionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get actions for a journey",
    description="Returns a list of actions/tasks that can be performed to complete a journey based on the provided journey summary.",
)
async def get_journey_actions(
    request: JourneySummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JourneyActionsResponse:
    """
    Get actions/tasks for a journey based on journey summary.
    
    This endpoint accepts a journey summary and returns a list of actions
    that can be performed to complete the journey. The actions are retrieved
    from the database based on the journey summary.
    
    Args:
        request: JourneySummaryRequest containing the journey summary
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        JourneyActionsResponse containing list of actions
        
    Raises:
        HTTPException: If the request is invalid or an error occurs
    """
    try:
        logger.info(
            f"Fetching actions for journey. User: {current_user.id}, "
            f"Summary length: {len(request.journeySummary)}"
        )
        
        actions = await JourneyService.get_actions_for_journey(
            db=db,
            journey_summary=request.journeySummary,
        )
        
        action_responses = [_action_to_response(action) for action in actions]
        
        logger.info(
            f"Successfully retrieved {len(action_responses)} actions for user: {current_user.id}"
        )
        
        return JourneyActionsResponse(actions=action_responses)
        
    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Invalid journey summary: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid journey summary: {error_message}",
        )
    except Exception as e:
        logger.error(
            f"Error fetching journey actions: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve journey actions",
        )
