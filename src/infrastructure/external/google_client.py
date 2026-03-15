import logging
import httpx
from typing import TypedDict

from src.config.settings import settings

logger = logging.getLogger(__name__)


class GoogleTokenResponse(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None
    id_token: str | None


class GoogleUserInfo(TypedDict):
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: str
    family_name: str
    picture: str | None


class GoogleOAuthClient:
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USER_INFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> GoogleTokenResponse:
        logger.info(f"Exchanging OAuth code. Redirect URI: {redirect_uri}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GoogleOAuthClient.TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=10.0,
            )
            
            if not response.is_success:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = str(error_json)
                except Exception:
                    pass
                
                logger.error(
                    f"Google OAuth token exchange failed. "
                    f"Status: {response.status_code}, "
                    f"Error: {error_detail}, "
                    f"Redirect URI sent: {redirect_uri}, "
                    f"Client ID: {settings.google_client_id[:20]}..."
                )
                response.raise_for_status()
            
            return response.json()

    @staticmethod
    async def get_user_info(access_token: str) -> GoogleUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GoogleOAuthClient.USER_INFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

