import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.domain.entities.journey import Action, Journey
from src.domain.value_objects.journey_trait import JourneyTrait
from src.infrastructure.database.models import (
    JourneyModel,
    JourneyActionModel,
)

logger = logging.getLogger(__name__)


class JourneyRepository:
    """Repository for journey database operations"""

    @staticmethod
    def save_journey(
        db: Session,
        summary: str,
        traits: list[JourneyTrait],
        actions: list[Action],
    ) -> Journey:
        """
        Save a journey to the database.

        Args:
            db: Database session
            summary: Journey summary
            traits: List of journey traits
            actions: List of actions

        Returns:
            Saved Journey entity
        """
        now = datetime.now(timezone.utc)

        traits_json = [
            {"name": trait.name, "confidence": trait.confidence}
            for trait in traits
        ]

        journey_model = JourneyModel(
            journey_summary=summary,
            journey_traits=traits_json,
            created_at=now,
            updated_at=now,
        )

        db.add(journey_model)
        db.flush()

        for action in actions:
            action_model = JourneyActionModel(
                journey_id=journey_model.id,
                action_title=action.title,
                action_duration=action.duration,
                action_steps=action.steps,
                action_order=action.order,
                is_completed=action.is_completed,
            )
            db.add(action_model)

        db.commit()
        db.refresh(journey_model)

        return JourneyRepository._model_to_entity(journey_model)

    @staticmethod
    def get_journey_by_id(
        db: Session,
        journey_id: str,
    ) -> Journey | None:
        """
        Get a journey by ID.

        Args:
            db: Database session
            journey_id: Journey UUID

        Returns:
            Journey entity or None
        """
        from uuid import UUID
        
        try:
            journey_uuid = UUID(journey_id)
        except ValueError:
            return None

        stmt = select(JourneyModel).where(JourneyModel.id == journey_uuid)
        journey_model = db.scalar(stmt)

        if not journey_model:
            return None

        return JourneyRepository._model_to_entity(journey_model)

    @staticmethod
    def _model_to_entity(journey_model: JourneyModel) -> Journey:
        """
        Convert database model to domain entity.

        Args:
            journey_model: Database model

        Returns:
            Journey domain entity
        """
        traits = [
            JourneyTrait(
                name=trait["name"],
                confidence=float(trait["confidence"]),
            )
            for trait in journey_model.journey_traits
        ]

        actions = []
        for action_model in sorted(journey_model.actions, key=lambda a: a.action_order):
            action = Action(
                id=action_model.id,
                title=action_model.action_title,
                duration=action_model.action_duration,
                steps=action_model.action_steps,
                order=action_model.action_order,
                is_completed=action_model.is_completed,
            )
            actions.append(action)

        return Journey(
            id=journey_model.id,
            summary=journey_model.journey_summary,
            traits=traits,
            actions=actions,
            created_at=journey_model.created_at,
            updated_at=journey_model.updated_at,
        )
