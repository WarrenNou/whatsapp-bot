"""
OpenClaw Integration Module
Connects to an OpenClaw Gateway instance for enhanced AI-powered responses.
OpenClaw is an open-source personal AI assistant (https://github.com/openclaw/openclaw)
that supports multiple messaging channels and extensible skills.

When an OpenClaw Gateway is available, messages are routed through it for richer
responses powered by OpenClaw skills. Falls back to direct OpenAI when unavailable.
"""

import requests
import logging
import os
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OpenClawClient:
    """Client for communicating with an OpenClaw Gateway instance."""

    def __init__(self):
        self.gateway_url = os.getenv('OPENCLAW_GATEWAY_URL', '')
        self.api_key = os.getenv('OPENCLAW_API_KEY', '')
        self.enabled = bool(self.gateway_url)
        try:
            self.timeout = int(os.getenv('OPENCLAW_TIMEOUT', '30'))
        except (ValueError, TypeError):
            self.timeout = 30
        self._available = None
        self._last_health_check = 0
        self._health_check_interval = 60  # Re-check every 60 seconds

        if self.enabled:
            logger.info(f"OpenClaw integration enabled, gateway: {self.gateway_url}")
        else:
            logger.info("OpenClaw integration disabled (OPENCLAW_GATEWAY_URL not set)")

    @property
    def is_available(self) -> bool:
        """Check if OpenClaw Gateway is reachable, with caching."""
        if not self.enabled:
            return False

        now = time.time()
        if self._available is not None and (now - self._last_health_check) < self._health_check_interval:
            return self._available

        self._available = self._check_health()
        self._last_health_check = now
        return self._available

    def _check_health(self) -> bool:
        """Ping the OpenClaw Gateway health endpoint."""
        try:
            resp = requests.get(
                f"{self.gateway_url}/api/health",
                headers=self._headers(),
                timeout=5
            )
            healthy = resp.status_code == 200
            if healthy:
                logger.debug("OpenClaw Gateway is healthy")
            else:
                logger.warning(f"OpenClaw Gateway returned status {resp.status_code}")
            return healthy
        except requests.RequestException as e:
            logger.warning(f"OpenClaw Gateway unreachable: {e}")
            return False

    def _headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'EVA-FX-Trading-Bot/3.1.0'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def send_message(self, message: str, conversation_id: Optional[str] = None,
                     channel: str = "web") -> Optional[Dict[str, Any]]:
        """
        Send a message to OpenClaw Gateway and get a response.

        Args:
            message: The user message text
            conversation_id: Optional conversation/session identifier
            channel: Channel identifier (web, whatsapp, telegram)

        Returns:
            Dict with 'response' text and metadata, or None if unavailable
        """
        if not self.is_available:
            return None

        try:
            payload = {
                'message': message,
                'channel': channel,
            }
            if conversation_id:
                payload['conversationId'] = conversation_id

            resp = requests.post(
                f"{self.gateway_url}/api/chat",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    'response': data.get('message', data.get('response', '')),
                    'source': 'openclaw',
                    'skills_used': data.get('skills', []),
                    'metadata': data.get('metadata', {})
                }
            else:
                logger.warning(f"OpenClaw chat returned status {resp.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"OpenClaw chat request failed: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get OpenClaw Gateway status information."""
        status = {
            'enabled': self.enabled,
            'available': self.is_available if self.enabled else False,
            'gateway_url': self.gateway_url if self.enabled else None,
        }

        if self.is_available:
            try:
                resp = requests.get(
                    f"{self.gateway_url}/api/health",
                    headers=self._headers(),
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status['version'] = data.get('version', 'unknown')
                    status['skills_count'] = data.get('skills', 0)
            except requests.RequestException:
                pass

        return status


# Module-level singleton
openclaw_client = OpenClawClient()
