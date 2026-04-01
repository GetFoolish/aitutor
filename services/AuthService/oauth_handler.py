"""
Google OAuth handler
"""
import os
from typing import Dict, Optional

from shared.logging_config import get_logger

logger = get_logger(__name__)


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


class GoogleOAuthHandler:
    """Handle Google OAuth flow"""
    
    def __init__(self, redirect_uri: str):
        self.redirect_uri = redirect_uri

    def _build_client(self, state: Optional[str] = None):
        from authlib.integrations.httpx_client import AsyncOAuth2Client

        return AsyncOAuth2Client(
            GOOGLE_CLIENT_ID,
            GOOGLE_CLIENT_SECRET,
            redirect_uri=self.redirect_uri,
            state=state,
        )
    
    def get_authorization_url(self) -> tuple[str, str]:
        """
        Get Google OAuth authorization URL
        
        Returns:
            Tuple of (authorization_url, state)
        """
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
        
        client = self._build_client()

        authorization_url, state = client.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            scope=['openid', 'email', 'profile']
        )
        
        return authorization_url, state
    
    async def get_user_info(self, code: str, state: str, authorization_response: str) -> Optional[Dict]:
        """
        Exchange authorization code for user info
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection
            
        Returns:
            Google user information dictionary
        """
        client = self._build_client(state=state)
        
        try:
            # Exchange code for token
            await client.fetch_token(
                'https://oauth2.googleapis.com/token',
                code=code,
                authorization_response=authorization_response,
            )
            
            # Get user info
            resp = await client.get('https://www.googleapis.com/oauth2/v2/userinfo')
            user_info = resp.json()
            
            return {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture", ""),
                "verified_email": user_info.get("verified_email", False)
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
        finally:
            await client.aclose()
