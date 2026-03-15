from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.value_objects.journey_trait import JourneyTrait


class Action:
    def __init__(
        self,
        id: UUID,
        title: str,
        duration: str,
        steps: list[str],
        order: int,
        is_completed: bool = False,
    ):
        self.id = id
        self.title = title
        self.duration = duration
        self.steps = steps
        self.order = order
        self.is_completed = is_completed

    @classmethod
    def create(
        cls,
        title: str,
        duration: str,
        steps: list[str],
        order: int,
        is_completed: bool = False,
    ) -> "Action":
        return cls(
            id=uuid4(),
            title=title,
            duration=duration,
            steps=steps,
            order=order,
            is_completed=is_completed,
        )


class Journey:
    def __init__(
        self,
        id: UUID,
        summary: str,
        traits: list[JourneyTrait],
        actions: list[Action],
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.summary = summary
        self.traits = traits
        self.actions = actions
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        summary: str,
        traits: list[JourneyTrait],
        actions: list[Action],
    ) -> "Journey":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            summary=summary,
            traits=traits,
            actions=actions,
            created_at=now,
            updated_at=now,
        )
