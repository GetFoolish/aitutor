"""
Run script for SherlockED API New

Start the Athena-based question service.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8011,
        reload=True
    )
