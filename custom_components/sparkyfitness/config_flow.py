"""Config flow for the SparkyFitness integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SparkyFitnessApiError, SparkyFitnessAuthError, SparkyFitnessClient
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


def _normalize_url(url: str) -> str:
    """Trim whitespace and trailing slashes from the URL."""
    return url.strip().rstrip("/")


async def _async_validate(hass, url: str, api_key: str) -> None:
    """Validate connection + auth by hitting the stats endpoint.

    Raises SparkyFitnessAuthError or SparkyFitnessApiError on failure.
    """
    session = async_get_clientsession(hass)
    client = SparkyFitnessClient(session, url, api_key)
    await client.async_get_stats()


class SparkyFitnessConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SparkyFitness."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = _normalize_url(user_input[CONF_URL])
            api_key = user_input[CONF_API_KEY].strip()

            if not urlparse(url).scheme:
                errors[CONF_URL] = "invalid_url"
            else:
                try:
                    await _async_validate(self.hass, url, api_key)
                except SparkyFitnessAuthError:
                    errors["base"] = "invalid_auth"
                except SparkyFitnessApiError:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(url)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=DEFAULT_NAME,
                        data={CONF_URL: url, CONF_API_KEY: api_key},
                    )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL,
                    default=(user_input or {}).get(CONF_URL, ""),
                ): str,
                vol.Required(CONF_API_KEY): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when the API key becomes invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth with a fresh API key."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                await _async_validate(self.hass, entry.data[CONF_URL], api_key)
            except SparkyFitnessAuthError:
                errors["base"] = "invalid_auth"
            except SparkyFitnessApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SparkyFitnessOptionsFlow:
        """Return the options flow handler."""
        return SparkyFitnessOptionsFlow()


class SparkyFitnessOptionsFlow(OptionsFlow):
    """Handle SparkyFitness options (polling interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
