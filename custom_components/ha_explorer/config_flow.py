"""Config flow for Home Assistant Explorer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    ShellyPresenceConnectionError,
    ShellyPresenceError,
    async_validate_shelly_presence,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_MAP_X,
    CONF_MAP_Y,
    CONF_MODEL,
    CONF_ROTATION,
    DEFAULT_MAP_X,
    DEFAULT_MAP_Y,
    DEFAULT_ROTATION,
    DOMAIN,
)


async def _async_validate_input(hass: HomeAssistant, host: str) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    return await async_validate_shelly_presence(session, host)


class ExplorerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Explorer."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return ExplorerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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


class ExplorerOptionsFlow(config_entries.OptionsFlow):
    """Configure floor-plan calibration for a Presence source."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage calibration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MAP_X,
                        default=options.get(CONF_MAP_X, DEFAULT_MAP_X),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_MAP_Y,
                        default=options.get(CONF_MAP_Y, DEFAULT_MAP_Y),
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_ROTATION,
                        default=options.get(CONF_ROTATION, DEFAULT_ROTATION),
                    ): vol.All(vol.Coerce(float), vol.Range(min=-360, max=360)),
                }
            ),
        )
