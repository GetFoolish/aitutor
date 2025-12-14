import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class InjectionManager:
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv("TUTOR_SERVER_URL", "http://localhost:8767")
        self.client = httpx.AsyncClient(timeout=5.0)

    async def send_to_adam(self, message: str, session_id: str, user_id: str) -> bool:
        try:
            response = await self.client.post(
                f"{self.server_url}/send_message_to_adam",
                json={
                    "session_id": session_id,
                    "user_id": user_id,
                    "message": message
                }
            )
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()

