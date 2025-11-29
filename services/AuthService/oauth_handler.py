"""
Google OAuth handler
"""
import os
from authlib.integrations.httpx_client import AsyncOAuth2Client
from typing import Dict, Optional

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


class GoogleOAuthHandler:
    """Handle Google OAuth flow"""
    
    def __init__(self, redirect_uri: str):
        self.redirect_uri = redirect_uri
        self.client = None
    
    def get_authorization_url(self) -> tuple[str, str]:
        """
        Get Google OAuth authorization URL
        
        Returns:
            Tuple of (authorization_url, state)
        """
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
        
        self.client = AsyncOAuth2Client(
            GOOGLE_CLIENT_ID,
            GOOGLE_CLIENT_SECRET,
            redirect_uri=self.redirect_uri
        )
        
        authorization_url, state = self.client.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            scope=['openid', 'email', 'profile']
        )
        
        return authorization_url, state
    
    async def get_user_info(self, code: str, state: str) -> Optional[Dict]:
        """
        Exchange authorization code for user info
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection
            
        Returns:
            Google user information dictionary
        """
        if not self.client:
            self.client = AsyncOAuth2Client(
                GOOGLE_CLIENT_ID,
                GOOGLE_CLIENT_SECRET,
                redirect_uri=self.redirect_uri
            )
        
        try:
            # Exchange code for token
            token = await self.client.fetch_token(
                'https://oauth2.googleapis.com/token',
                code=code,
                authorization_response=None
            )
            
            # Get user info
            resp = await self.client.get('https://www.googleapis.com/oauth2/v2/userinfo')
            user_info = resp.json()
            
            return {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture", ""),
                "verified_email": user_info.get("verified_email", False)
            }
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

