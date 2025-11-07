import sys
import os

# Add parent directory to path so config_manager can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
import uvicorn

# Import and include auth routes
from auth.auth_routes import router as auth_router
app.include_router(auth_router)

# Import and include payment routes
from payments.payment_routes import router as payment_router
app.include_router(payment_router) 

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8001,
        reload=True
    )