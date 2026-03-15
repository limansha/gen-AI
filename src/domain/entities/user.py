from datetime import datetime, timezone
from uuid import UUID, uuid4


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        name: str,
        google_id: str,
        created_at: datetime,
        updated_at: datetime,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.google_id = google_id
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def create(
        cls,
        email: str,
        name: str,
        google_id: str,
    ) -> "User":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            email=email,
            name=name,
            google_id=google_id,
            created_at=now,
            updated_at=now,
        )

    def update_name(self, name: str) -> None:
        self.name = name
        self.updated_at = datetime.now(timezone.utc)

