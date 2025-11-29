"""
Shared JWT configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

