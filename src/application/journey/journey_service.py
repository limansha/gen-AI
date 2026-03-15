import logging
from sqlalchemy.orm import Session

from src.domain.entities.journey import Action
from src.application.journey.journey_workflow import JourneyWorkflow

logger = logging.getLogger(__name__)


class JourneyService:
    _workflow: JourneyWorkflow | None = None

    @classmethod
    def _get_workflow(cls) -> JourneyWorkflow:
        """Lazy initialization of workflow"""
        if cls._workflow is None:
            cls._workflow = JourneyWorkflow()
        return cls._workflow

    @staticmethod
    async def get_actions_for_journey(
        db: Session,
        journey_summary: str,
    ) -> list[Action]:
        """
        Retrieve actions/tasks for a given journey summary using LangGraph workflow.
        
        The workflow:
        1. Validates input with guardrails
        2. Checks if journey exists in database
        3. If exists: retrieves from DB
        4. If not: understands user needs, generates actions/traits, saves to DB
        5. Returns list of actions
        
        Args:
            db: Database session
            journey_summary: The journey summary text
            
        Returns:
            List of Action entities
            
        Raises:
            ValueError: If workflow execution fails or validation fails
        """
        workflow = JourneyService._get_workflow()
        
        try:
            actions = await workflow.execute(journey_summary, db)
            logger.info(f"Successfully retrieved {len(actions)} actions for journey")
            return actions
        except Exception as e:
            logger.error(f"Failed to get actions for journey: {str(e)}", exc_info=True)
            raise
