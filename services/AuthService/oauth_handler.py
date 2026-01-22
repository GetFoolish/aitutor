"""
Google OAuth handler
"""
import os
from authlib.integrations.httpx_client import AsyncOAuth2Client
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
        self.client = None
    
    def get_authorization_url(self) -> tuple[str, str]:
        """
        Get Google OAuth authorization URL with People API scopes
        
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
        
        # Add People API scopes for birthday and gender
        scopes = [
            'openid',
            'email',
            'profile',
            'https://www.googleapis.com/auth/user.birthday.read',
            'https://www.googleapis.com/auth/user.gender.read'
        ]
        
        authorization_url, state = self.client.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            scope=scopes
        )
        
        return authorization_url, state
    
    async def get_user_info(self, code: str, state: str) -> Optional[Dict]:
        """
        Exchange authorization code for user info from OAuth and People API
        
        Args:
            code: Authorization code from Google
            state: State parameter for CSRF protection
            
        Returns:
            Google user information dictionary with optional birthday and gender
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
            
            # Get basic user info from OAuth
            resp = await self.client.get('https://www.googleapis.com/oauth2/v2/userinfo')
            user_info = resp.json()
            
            result = {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture", ""),
                "verified_email": user_info.get("verified_email", False),
                "birthday": None,
                "gender": None
            }
            
            # Try to fetch birthday and gender from People API
            try:
                people_resp = await self.client.get(
                    'https://people.googleapis.com/v1/people/me',
                    params={
                        'personFields': 'birthdays,genders'
                    }
                )
                
                if people_resp.status_code == 200:
                    people_data = people_resp.json()
                    
                    # Extract birthday
                    birthdays = people_data.get('birthdays', [])
                    if birthdays:
                        # Google returns birthday in various formats, handle the most common
                        for bday in birthdays:
                            date = bday.get('date', {})
                            if date:
                                year = date.get('year', 2000)  # Default if year not provided
                                month = date.get('month', 1)
                                day = date.get('day', 1)
                                # Format as YYYY-MM-DD
                                result["birthday"] = f"{year:04d}-{month:02d}-{day:02d}"
                                break
                    
                    # Extract gender
                    genders = people_data.get('genders', [])
                    if genders:
                        gender_value = genders[0].get('value', '').lower()
                        # Map Google gender values to our format
                        gender_map = {
                            'male': 'Male',
                            'female': 'Female',
                            'other': 'Other'
                        }
                        result["gender"] = gender_map.get(gender_value, None)
                
            except Exception as e:
                # People API call failed - user may have private settings or denied permission
                logger.info(f"Could not fetch birthday/gender from People API: {e}")
                # Continue with None values - form will require manual entry
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

