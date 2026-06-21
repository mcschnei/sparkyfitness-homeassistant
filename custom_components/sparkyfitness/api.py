"""API client for SparkyFitness."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    CHECKIN_RANGE_ENDPOINT,
    CUSTOM_CATEGORIES_ENDPOINT,
    CUSTOM_ENTRIES_ENDPOINT,
    REQUEST_TIMEOUT,
    SLEEP_ENDPOINT,
    STATS_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class SparkyFitnessApiError(Exception):
    """Generic SparkyFitness API error (connection / unexpected response)."""


class SparkyFitnessAuthError(SparkyFitnessApiError):
    """Raised when the API key is missing, invalid or lacks permission."""


class SparkyFitnessClient:
    """Small async client for the SparkyFitness REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_key: str,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        """Auth headers.

        SparkyFitness accepts the API key either as a Bearer token or via the
        X-API-Key header. We send both so we work regardless of which the
        deployment expects.
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    async def _async_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Perform a GET request and return decoded JSON.

        Raises SparkyFitnessAuthError on 401/403 and SparkyFitnessApiError on
        any other failure.
        """
        url = f"{self._base_url}{endpoint}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(
                    url, headers=self._headers, params=params
                )
        except asyncio.TimeoutError as err:
            raise SparkyFitnessApiError(
                f"Timeout connecting to SparkyFitness at {url}"
            ) from err
        except aiohttp.ClientError as err:
            raise SparkyFitnessApiError(
                f"Error connecting to SparkyFitness: {err}"
            ) from err

        if response.status in (401, 403):
            raise SparkyFitnessAuthError(
                "Authentication failed — check the API key and that it has the "
                "required permission."
            )
        if response.status != 200:
            text = await response.text()
            raise SparkyFitnessApiError(
                f"Unexpected response {response.status} from SparkyFitness: {text[:200]}"
            )

        try:
            return await response.json()
        except (aiohttp.ContentTypeError, ValueError) as err:
            raise SparkyFitnessApiError(
                "SparkyFitness returned a non-JSON response. Check the URL points "
                "at the SparkyFitness server/frontend, not a login page."
            ) from err

    async def async_get_stats(self) -> dict[str, Any]:
        """Fetch today's dashboard stats (eaten/burned/remaining/steps)."""
        data = await self._async_request(STATS_ENDPOINT)
        if not isinstance(data, dict):
            raise SparkyFitnessApiError(
                f"Unexpected JSON shape from SparkyFitness stats: {type(data).__name__}"
            )
        return data

    @staticmethod
    def _as_list(data: Any, label: str) -> list[dict[str, Any]]:
        """Coerce a response into a list of dicts.

        Accepts a bare list, or an object wrapping the list under a common key.
        """
        if isinstance(data, dict):
            for key in ("data", "entries", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            raise SparkyFitnessApiError(
                f"Unexpected JSON shape from SparkyFitness {label}: {type(data).__name__}"
            )
        return [entry for entry in data if isinstance(entry, dict)]

    async def async_get_sleep(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch sleep entries between two YYYY-MM-DD dates (inclusive)."""
        data = await self._async_request(
            SLEEP_ENDPOINT, params={"startDate": start_date, "endDate": end_date}
        )
        return self._as_list(data, "sleep")

    async def async_get_checkin_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch standard check-in measurements (weight, body fat %, ...)."""
        endpoint = f"{CHECKIN_RANGE_ENDPOINT}/{start_date}/{end_date}"
        data = await self._async_request(endpoint)
        return self._as_list(data, "check-in measurements")

    async def async_get_custom_categories(self) -> list[dict[str, Any]]:
        """Fetch the user's custom measurement categories."""
        data = await self._async_request(CUSTOM_CATEGORIES_ENDPOINT)
        return self._as_list(data, "custom categories")

    async def async_get_custom_entries(
        self, limit: int
    ) -> list[dict[str, Any]]:
        """Fetch recent custom-measurement entries (newest first)."""
        data = await self._async_request(
            CUSTOM_ENTRIES_ENDPOINT,
            params={"limit": limit, "orderBy": "entry_timestamp.desc"},
        )
        return self._as_list(data, "custom entries")
