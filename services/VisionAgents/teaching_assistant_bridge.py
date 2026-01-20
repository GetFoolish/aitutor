"""
TeachingAssistant Bridge for Vision Agents
Sends audio/visual signals from Vision Agents to TeachingAssistant for struggle detection.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger(__name__)


class TeachingAssistantBridge:
    """
    Bridge class that sends processor signals to TeachingAssistant.
    Handles communication with the /signals/update endpoint.
    """

    def __init__(self, ta_url: str = "http://localhost:8002"):
        """
        Initialize the bridge.

        Args:
            ta_url: TeachingAssistant service URL
        """
        self.ta_url = ta_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False

        logger.info(f"[TA_BRIDGE] Initialized with URL: {ta_url}")

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def send_signals(
        self,
        session_id: str,
        signals: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Send audio/visual signals to TeachingAssistant.

        Args:
            session_id: Student session ID
            signals: Dictionary with 'audio' and 'visual' signal data

        Returns:
            Response from TeachingAssistant including any intervention
        """
        try:
            session = await self._ensure_session()

            payload = {
                "session_id": session_id,
                "audio_signals": signals.get("audio", {}),
                "visual_signals": signals.get("visual", {}),
            }

            url = f"{self.ta_url}/signals/update"

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if not self._connected:
                        self._connected = True
                        logger.info("[TA_BRIDGE] Connected to TeachingAssistant")

                    # Log if intervention was triggered
                    if result.get("intervention"):
                        logger.info(
                            f"[TA_BRIDGE] Intervention received: {result['intervention']}"
                        )

                    return result
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"[TA_BRIDGE] Failed to send signals: {response.status} - {error_text}"
                    )
                    return None

        except aiohttp.ClientConnectorError:
            if self._connected:
                self._connected = False
                logger.warning("[TA_BRIDGE] Lost connection to TeachingAssistant")
            return None
        except asyncio.TimeoutError:
            logger.warning("[TA_BRIDGE] Timeout sending signals")
            return None
        except Exception as e:
            logger.error(f"[TA_BRIDGE] Error sending signals: {e}")
            return None

    async def check_health(self) -> bool:
        """
        Check if TeachingAssistant service is healthy.

        Returns:
            True if service is responding, False otherwise
        """
        try:
            session = await self._ensure_session()
            url = f"{self.ta_url}/health"

            async with session.get(url) as response:
                return response.status == 200

        except Exception as e:
            logger.warning(f"[TA_BRIDGE] Health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("[TA_BRIDGE] Session closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
