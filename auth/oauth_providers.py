"""
OAuth Provider Integrations (Production-Ready)
Google, Apple, Facebook OAuth flows
"""
import os
from typing import Optional, Dict
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID", "")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")
APPLE_PRIVATE_KEY_PATH = os.getenv("APPLE_PRIVATE_KEY_PATH", "")

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")


class OAuthProvider:
    """Base class for OAuth providers"""

    @staticmethod
    def verify_google_token(id_token_str: str) -> Optional[Dict]:
        """
        Verify Google ID token and return user info.

        Frontend should use Google Sign-In library to get id_token.
        Documentation: https://developers.google.com/identity/gsi/web/guides/overview

        Args:
            id_token_str: The ID token from Google Sign-In

        Returns:
            User info dict or None if invalid
        """
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable."
            )

        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )

            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            # Extract user info
            return {
                'oauth_id': idinfo['sub'],
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False)
            }

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )

    @staticmethod
    def verify_apple_token(id_token_str: str) -> Optional[Dict]:
        """
        Verify Apple ID token.

        Frontend should use Sign in with Apple JS SDK.
        Documentation: https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_js

        Args:
            id_token_str: The ID token from Apple Sign-In

        Returns:
            User info dict or None if invalid
        """
        if not APPLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Apple OAuth not configured. Set APPLE_CLIENT_ID environment variable."
            )

        try:
            # Import Apple-specific libraries
            import jwt
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # Decode without verification first to get the header
            unverified_header = jwt.get_unverified_header(id_token_str)

            # Fetch Apple's public keys
            import requests
            keys_response = requests.get('https://appleid.apple.com/auth/keys')
            apple_keys = keys_response.json()['keys']

            # Find the matching key
            kid = unverified_header['kid']
            matching_key = None
            for key in apple_keys:
                if key['kid'] == kid:
                    matching_key = key
                    break

            if not matching_key:
                raise ValueError('No matching Apple public key found')

            # Verify and decode
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(matching_key)

            decoded = jwt.decode(
                id_token_str,
                public_key,
                audience=APPLE_CLIENT_ID,
                algorithms=['RS256']
            )

            return {
                'oauth_id': decoded['sub'],
                'email': decoded.get('email'),
                'name': 'Apple User',  # Apple doesn't always provide name
                'picture': None,
                'email_verified': decoded.get('email_verified') == 'true'
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Apple token: {str(e)}"
            )

    @staticmethod
    def verify_facebook_token(access_token: str) -> Optional[Dict]:
        """
        Verify Facebook access token and get user info.

        Frontend should use Facebook SDK for JavaScript.
        Documentation: https://developers.facebook.com/docs/facebook-login/web

        Args:
            access_token: The access token from Facebook Login

        Returns:
            User info dict or None if invalid
        """
        if not FACEBOOK_APP_ID or not FACEBOOK_APP_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Facebook OAuth not configured."
            )

        try:
            import requests

            # Verify token with Facebook
            verify_url = 'https://graph.facebook.com/debug_token'
            params = {
                'input_token': access_token,
                'access_token': f"{FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}"
            }

            response = requests.get(verify_url, params=params)
            token_data = response.json()

            if not token_data.get('data', {}).get('is_valid'):
                raise ValueError('Invalid Facebook token')

            # Get user info
            user_url = 'https://graph.facebook.com/me'
            user_params = {
                'fields': 'id,name,email,picture.type(large)',
                'access_token': access_token
            }

            user_response = requests.get(user_url, params=user_params)
            user_data = user_response.json()

            return {
                'oauth_id': user_data['id'],
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture', {}).get('data', {}).get('url'),
                'email_verified': True  # Facebook email is verified
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Facebook token: {str(e)}"
            )


# Frontend Integration Instructions
"""
=== GOOGLE OAUTH INTEGRATION ===

1. Create OAuth credentials:
   - Go to: https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID
   - Add authorized JavaScript origins: http://localhost:3000
   - Copy Client ID to .env as GOOGLE_CLIENT_ID

2. Frontend (React):
   ```bash
   npm install @react-oauth/google
   ```

   ```tsx
   import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

   <GoogleOAuthProvider clientId={process.env.REACT_APP_GOOGLE_CLIENT_ID}>
     <GoogleLogin
       onSuccess={(credentialResponse) => {
         // Send credentialResponse.credential (id_token) to backend
         fetch('/auth/oauth/google', {
           method: 'POST',
           body: JSON.stringify({ id_token: credentialResponse.credential })
         });
       }}
       onError={() => console.log('Login Failed')}
     />
   </GoogleOAuthProvider>
   ```

=== APPLE OAUTH INTEGRATION ===

1. Setup Apple Developer:
   - Go to: https://developer.apple.com/account/resources/identifiers
   - Create Services ID
   - Configure Sign in with Apple
   - Download private key

2. Frontend (React):
   ```bash
   npm install react-apple-signin-auth
   ```

   ```tsx
   import AppleSignin from 'react-apple-signin-auth';

   <AppleSignin
     authOptions={{
       clientId: process.env.REACT_APP_APPLE_CLIENT_ID,
       scope: 'email name',
       redirectURI: 'http://localhost:3000/auth/apple/callback',
       usePopup: true,
     }}
     onSuccess={(response) => {
       // Send response.authorization.id_token to backend
     }}
   />
   ```

=== FACEBOOK OAUTH INTEGRATION ===

1. Create Facebook App:
   - Go to: https://developers.facebook.com/apps
   - Create app, add Facebook Login product
   - Add http://localhost:3000 to Valid OAuth Redirect URIs

2. Frontend (React):
   ```bash
   npm install react-facebook-login
   ```

   ```tsx
   import FacebookLogin from 'react-facebook-login';

   <FacebookLogin
     appId={process.env.REACT_APP_FACEBOOK_APP_ID}
     fields="name,email,picture"
     callback={(response) => {
       // Send response.accessToken to backend
     }}
   />
   ```
"""
