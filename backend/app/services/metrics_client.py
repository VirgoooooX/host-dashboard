"""Host metrics HTTP client — fetches /metrics/json from exporter.

Each host runs its own host-metrics-exporter instance (deployed as a separate
container). The exporter returns a JSON blob with CPU, memory, disk, load, uptime.
"""

import logging
from typing import Optional

import httpx

from app.models import HostConfig
from app.services.crypto import decrypt_authorization_header
from app.schemas import HostMetrics

logger = logging.getLogger(__name__)


class MetricsClient:
    """HTTP client for one host-metrics-exporter instance."""

    def __init__(self, config: HostConfig):
        self._host_id = config.host_id
        self._url = config.metrics_url.rstrip("/") + "/metrics/json"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
        )

        if config.metrics_auth_encrypted:
            try:
                self._auth_header = decrypt_authorization_header(
                    config.metrics_auth_encrypted
                )
            except ValueError:
                logger.error(
                    "Failed to decrypt metrics auth for %s", config.host_id
                )
                self._auth_header = None
        else:
            self._auth_header = None

    async def fetch(self) -> Optional[HostMetrics]:
        """Fetch and return parsed metrics. Returns None on any error."""
        headers = {"Authorization": self._auth_header} if self._auth_header else {}
        try:
            r = await self._client.get(self._url, headers=headers)
            r.raise_for_status()
            data = r.json()
            return HostMetrics(**data)
        except Exception as exc:
            logger.debug("Metrics fetch failed for %s: %s", self._host_id, exc)
            return None

    async def close(self) -> None:
        await self._client.aclose()
