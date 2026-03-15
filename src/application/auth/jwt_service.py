import logging
from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID

from jose import jwt, JWTError

from src.config.settings import settings

logger = logging.getLogger(__name__)


class JWTPayload(TypedDict):
    user_id: str
    email: str
    exp: int
    iat: int
    token_type: str


class RefreshTokenPayload(TypedDict):
    user_id: str
    email: str
    exp: int
    iat: int
    token_type: str


class JWTService:
    @staticmethod
    def generate_token(user_id: UUID, email: str) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload: JWTPayload = {
            "user_id": str(user_id),
            "email": email,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "token_type": "access",
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    @staticmethod
    def generate_refresh_token(user_id: UUID, email: str) -> str:
        now = datetime.now(timezone.utc)
        expire = now + timedelta(
            minutes=settings.jwt_refresh_token_expire_minutes
        )
        payload: RefreshTokenPayload = {
            "user_id": str(user_id),
            "email": email,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "token_type": "refresh",
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    @staticmethod
    def validate_token(token: str) -> JWTPayload:
        if not token or not isinstance(token, str):
            logger.warning("Token validation failed: token must be a non-empty string")
            raise ValueError("Token must be a non-empty string")
        
        token = token.strip()
        
        if not token:
            logger.warning("Token validation failed: token is empty after stripping whitespace")
            raise ValueError("Token cannot be empty after stripping")
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            
            if payload.get("token_type") != "access":
                logger.warning("Token validation failed: invalid token type")
                raise ValueError("Invalid token type")
            
            return JWTPayload(
                user_id=payload["user_id"],
                email=payload["email"],
                exp=payload["exp"],
                iat=payload["iat"],
                token_type=payload["token_type"],
            )
        except JWTError as e:
            error_message = str(e)
            logger.warning(f"JWT decode error: {error_message}")
            raise ValueError(f"Invalid or expired token: {error_message}")

    @staticmethod
    def validate_refresh_token(token: str) -> RefreshTokenPayload:
        if not token or not isinstance(token, str):
            logger.warning("Refresh token validation failed: token must be a non-empty string")
            raise ValueError("Refresh token must be a non-empty string")
        
        token = token.strip()
        
        if not token:
            logger.warning("Refresh token validation failed: token is empty after stripping whitespace")
            raise ValueError("Refresh token cannot be empty after stripping")
        
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            
            if payload.get("token_type") != "refresh":
                logger.warning("Refresh token validation failed: invalid token type")
                raise ValueError("Invalid token type")
            
            return RefreshTokenPayload(
                user_id=payload["user_id"],
                email=payload["email"],
                exp=payload["exp"],
                iat=payload["iat"],
                token_type=payload["token_type"],
            )
        except JWTError as e:
            error_message = str(e)
            logger.warning(f"JWT decode error for refresh token: {error_message}")
            raise ValueError(f"Invalid or expired refresh token: {error_message}")

