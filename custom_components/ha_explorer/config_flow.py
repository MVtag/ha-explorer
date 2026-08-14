"""Config flow for Home Assistant Explorer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    ShellyPresenceConnectionError,
    ShellyPresenceError,
    async_validate_shelly_presence,
)
from .const import CONF_DEVICE_ID, CONF_MODEL, DOMAIN


async def _async_validate_input(hass: HomeAssistant, host: str) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    return await async_validate_shelly_presence(session, host)


class ExplorerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Explorer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                info = await _async_validate_input(self.hass, host)
            except ShellyPresenceConnectionError:
                errors["base"] = "cannot_connect"
            except ShellyPresenceError:
                errors["base"] = "not_supported"
            except Exception:  # noqa: BLE001 - config flow must show generic failure
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(info["device_id"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title="Shelly Presence Gen4",
                    data={
                        CONF_HOST: host,
                        CONF_DEVICE_ID: info["device_id"],
                        CONF_MODEL: info["model"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )
