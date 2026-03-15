from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.domain.entities.user import User
from src.infrastructure.database.models import UserModel


class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        user_model = db.scalar(stmt)

        if not user_model:
            return None

        return User(
            id=user_model.id,
            email=user_model.email,
            name=user_model.name,
            google_id=user_model.google_id,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
        )

