"""The SparkyFitness integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SparkyFitnessClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import SparkyFitnessCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

SparkyFitnessConfigEntry = ConfigEntry[SparkyFitnessCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: SparkyFitnessConfigEntry
) -> bool:
    """Set up SparkyFitness from a config entry."""
    session = async_get_clientsession(hass)
    client = SparkyFitnessClient(
        session,
        entry.data[CONF_URL],
        entry.data[CONF_API_KEY],
    )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = SparkyFitnessCoordinator(hass, entry, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: SparkyFitnessConfigEntry
) -> None:
    """Reload the entry when options change (e.g. scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SparkyFitnessConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
