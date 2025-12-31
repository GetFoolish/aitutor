"""
Run script for SherlockED API New

Start the Athena-based question service.
"""

import uvicorn
from dotenv import load_dotenv, find_dotenv

# Initialize environment variables before any other imports
load_dotenv(find_dotenv())

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8010,
        reload=True
    )
