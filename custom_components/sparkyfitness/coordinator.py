"""DataUpdateCoordinator for SparkyFitness."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SparkyFitnessApiError, SparkyFitnessAuthError, SparkyFitnessClient
from .const import (
    BODY_LOOKBACK_DAYS,
    CHECKIN_ENTRY_DATE,
    CUSTOM_ENTRIES_LIMIT,
    DOMAIN,
    SLEEP_ENTRY_DATE,
    SLEEP_LOOKBACK_DAYS,
)

_LOGGER = logging.getLogger(__name__)


def _pick_latest_sleep(
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the most recent sleep entry (by entry_date, then bedtime)."""
    if not entries:
        return None

    def _sort_key(entry: dict[str, Any]) -> str:
        return str(entry.get(SLEEP_ENTRY_DATE) or entry.get("bedtime") or "")

    return max(entries, key=_sort_key)


def _pick_latest_checkin(
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the most recent check-in measurement entry."""
    if not entries:
        return None
    return max(entries, key=lambda e: str(e.get(CHECKIN_ENTRY_DATE) or ""))


def _build_custom_map(
    categories: list[dict[str, Any]],
    entries: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map each custom category to its most recent value.

    Returns {category_id: {name, unit, value, date}}. Entries are assumed to be
    sorted newest-first, so the first one seen per category is the latest.
    """
    cat_by_id = {str(c.get("id")): c for c in categories if c.get("id")}
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        cat_id = str(entry.get("category_id") or "")
        if not cat_id or cat_id in result:
            continue
        # Prefer category info embedded in the entry, fall back to the list.
        cat = entry.get("custom_categories") or cat_by_id.get(cat_id) or {}
        name = cat.get("display_name") or cat.get("name") or f"Custom {cat_id[:8]}"
        result[cat_id] = {
            "name": name,
            "unit": cat.get("measurement_type"),
            "value": entry.get("value"),
            "date": entry.get("entry_date"),
        }
    return result


class SparkyFitnessCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls SparkyFitness for dashboard stats and sleep."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SparkyFitnessClient,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
            config_entry=entry,
        )
        self.client = client
        # Warn only once per optional section if its endpoint rejects our key.
        self._sleep_warned = False
        self._body_warned = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch stats (required) and sleep (best-effort)."""
        # Dashboard stats are the core data — a failure here is fatal.
        try:
            stats = await self.client.async_get_stats()
        except SparkyFitnessAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SparkyFitnessApiError as err:
            raise UpdateFailed(str(err)) from err

        today = dt_util.now().date()

        # Sleep is optional: never let it break the calorie/steps sensors.
        sleep: dict[str, Any] | None = None
        sleep_start = (today - timedelta(days=SLEEP_LOOKBACK_DAYS)).isoformat()
        try:
            entries = await self.client.async_get_sleep(sleep_start, today.isoformat())
            sleep = _pick_latest_sleep(entries)
        except SparkyFitnessAuthError:
            if not self._sleep_warned:
                _LOGGER.warning(
                    "SparkyFitness sleep endpoint rejected the API key. Sleep "
                    "sensors will be unavailable. The key may lack sleep-read "
                    "permission, or this endpoint may require a login session."
                )
                self._sleep_warned = True
        except SparkyFitnessApiError as err:
            _LOGGER.debug("Could not fetch SparkyFitness sleep data: %s", err)

        # Body composition is optional too. Weight + body fat come from the
        # standard check-in range; muscle/fat/bone mass are custom categories.
        body: dict[str, Any] | None = None
        custom: dict[str, dict[str, Any]] = {}
        body_start = (today - timedelta(days=BODY_LOOKBACK_DAYS)).isoformat()
        try:
            checkins = await self.client.async_get_checkin_range(
                body_start, today.isoformat()
            )
            body = _pick_latest_checkin(checkins)

            categories = await self.client.async_get_custom_categories()
            entries = await self.client.async_get_custom_entries(CUSTOM_ENTRIES_LIMIT)
            custom = _build_custom_map(categories, entries)
        except SparkyFitnessAuthError:
            if not self._body_warned:
                _LOGGER.warning(
                    "SparkyFitness measurement endpoints rejected the API key. "
                    "Weight and body-composition sensors will be unavailable."
                )
                self._body_warned = True
        except SparkyFitnessApiError as err:
            _LOGGER.debug("Could not fetch SparkyFitness body data: %s", err)

        return {"stats": stats, "sleep": sleep, "body": body, "custom": custom}
