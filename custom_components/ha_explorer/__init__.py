"""Home Assistant Explorer integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import ShellyPresenceClient
from .const import DOMAIN, PLATFORMS


type ExplorerConfigEntry = ConfigEntry[ShellyPresenceClient]


async def _async_options_updated(hass: HomeAssistant, entry: ExplorerConfigEntry) -> None:
    """Reload Explorer when floor-plan calibration options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ExplorerConfigEntry) -> bool:
    """Set up Home Assistant Explorer from a config entry."""
    session = async_get_clientsession(hass)
    source = f"ha-explorer-{entry.entry_id[:8]}"
    client = ShellyPresenceClient(session, entry.data["host"], source)
    entry.runtime_data = client

    await client.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ExplorerConfigEntry) -> bool:
    """Unload a Home Assistant Explorer config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok
