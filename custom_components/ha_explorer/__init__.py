"""Home Assistant Explorer integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import ShellyPresenceClient
from .const import CONF_DEVICE_ID, DOMAIN, PLATFORMS


type ExplorerConfigEntry = ConfigEntry[ShellyPresenceClient]


async def async_setup_entry(hass: HomeAssistant, entry: ExplorerConfigEntry) -> bool:
    """Set up Home Assistant Explorer from a config entry."""
    session = async_get_clientsession(hass)
    source = f"ha-explorer-{entry.entry_id[:8]}"
    client = ShellyPresenceClient(session, entry.data["host"], source)
    entry.runtime_data = client

    await client.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ExplorerConfigEntry) -> bool:
    """Unload a Home Assistant Explorer config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok
