from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.domain.entities.user import User
from src.infrastructure.database.models import UserModel
from src.infrastructure.external.google_client import (
    GoogleOAuthClient,
    GoogleUserInfo,
)


class GoogleOAuthService:
    @staticmethod
    async def exchange_code_and_get_user_info(
        code: str, redirect_uri: str
    ) -> GoogleUserInfo:
        token_response = await GoogleOAuthClient.exchange_code_for_token(
            code, redirect_uri
        )
        access_token = token_response["access_token"]
        user_info = await GoogleOAuthClient.get_user_info(access_token)
        return user_info

    @staticmethod
    def get_or_create_user(
        db: Session, google_user_info: GoogleUserInfo
    ) -> User:
        stmt = select(UserModel).where(
            UserModel.google_id == google_user_info["id"]
        )
        user_model = db.scalar(stmt)

        if user_model:
            if user_model.name != google_user_info["name"]:
                user_model.name = google_user_info["name"]
                user_model.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(user_model)
            return User(
                id=user_model.id,
                email=user_model.email,
                name=user_model.name,
                google_id=user_model.google_id,
                created_at=user_model.created_at,
                updated_at=user_model.updated_at,
            )

        new_user = User.create(
            email=google_user_info["email"],
            name=google_user_info["name"],
            google_id=google_user_info["id"],
        )

        user_model = UserModel(
            id=new_user.id,
            email=new_user.email,
            name=new_user.name,
            google_id=new_user.google_id,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
        )
        db.add(user_model)
        db.commit()
        db.refresh(user_model)

        return User(
            id=user_model.id,
            email=user_model.email,
            name=user_model.name,
            google_id=user_model.google_id,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
        )

