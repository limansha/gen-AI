import logging
import httpx
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.application.auth.google_oauth_service import GoogleOAuthService
from src.application.auth.jwt_service import JWTService
from src.domain.entities.user import User
from src.infrastructure.database.connection import get_db
from src.presentation.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCallbackRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=500)
    redirect_uri: str = Field(..., min_length=1, max_length=500)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(BaseModel):
    message: str = "Successfully logged out"


@router.post("/google/callback", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def google_callback(
    request: GoogleCallbackRequest,
    db: Session = Depends(get_db),
):
    try:
        logger.info(f"OAuth callback received. Redirect URI: {request.redirect_uri}")
        
        google_user_info = await GoogleOAuthService.exchange_code_and_get_user_info(
            request.code, request.redirect_uri
        )

        if not google_user_info.get("verified_email", False):
            email = google_user_info.get("email", "[EMAIL_REDACTED]")
            logger.warning(f"Unverified email attempted: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not verified",
            )

        user = GoogleOAuthService.get_or_create_user(db, google_user_info)
        access_token = JWTService.generate_token(user.id, user.email)
        refresh_token = JWTService.generate_refresh_token(user.id, user.email)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            f"OAuth token exchange HTTP error: {e.response.status_code} - {e.response.text}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth token exchange failed: {e.response.text[:200]}",
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/refresh", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        refresh_token_payload = JWTService.validate_refresh_token(request.refresh_token)
        from uuid import UUID
        user_id = UUID(refresh_token_payload["user_id"])
        email = refresh_token_payload["email"]
        
        from src.application.user.user_service import UserService
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for refresh token: user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        new_access_token = JWTService.generate_token(user.id, user.email)
        new_refresh_token = JWTService.generate_refresh_token(user.id, user.email)
        
        return AuthResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    except ValueError as e:
        error_message = str(e)
        logger.warning(f"Refresh token validation failed: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {error_message}",
        )
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user),
):
    try:
        user_id = str(current_user.id)
        email = current_user.email
        logger.info(f"User logout: user_id={user_id}, email={email}")
        return LogoutResponse(message="Successfully logged out")
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )

