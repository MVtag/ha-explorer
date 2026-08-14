"""Sensor platform for Home Assistant Explorer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import ShellyPresenceClient
from .const import CONF_DEVICE_ID, CONF_MODEL, DOMAIN, MAX_TARGET_SLOTS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ShellyPresenceClient],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Explorer sensors."""
    client = entry.runtime_data
    entities: list[SensorEntity] = [ExplorerTargetsSensor(entry, client)]
    entities.extend(
        ExplorerTargetSensor(entry, client, slot)
        for slot in range(1, MAX_TARGET_SLOTS + 1)
    )
    async_add_entities(entities)


class ExplorerBaseSensor(SensorEntity):
    """Base class for Explorer sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry[ShellyPresenceClient], client: ShellyPresenceClient) -> None:
        self._entry = entry
        self._client = client
        self._remove_listener = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.data[CONF_DEVICE_ID]))},
            name="Shelly Presence Gen4",
            manufacturer="Shelly",
            model=entry.data.get(CONF_MODEL, "Shelly Presence Gen4"),
            configuration_url=f"http://{entry.data['host']}",
        )

    async def async_added_to_hass(self) -> None:
        """Register for live target updates."""
        self._remove_listener = self._client.add_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister live target updates."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._client.connected


class ExplorerTargetsSensor(ExplorerBaseSensor):
    """Summary sensor for all currently tracked targets."""

    _attr_name = "Targets"
    _attr_icon = "mdi:radar"

    def __init__(self, entry: ConfigEntry[ShellyPresenceClient], client: ShellyPresenceClient) -> None:
        super().__init__(entry, client)
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_targets"

    @property
    def native_value(self) -> int:
        return len(self._client.targets)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "targets": self._client.target_list,
            "host": self._client.host,
        }


class ExplorerTargetSensor(ExplorerBaseSensor):
    """Expose one live target slot."""

    _attr_icon = "mdi:account-location"

    def __init__(
        self,
        entry: ConfigEntry[ShellyPresenceClient],
        client: ShellyPresenceClient,
        slot: int,
    ) -> None:
        super().__init__(entry, client)
        self._slot = slot
        self._attr_name = f"Target {slot}"
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_target_{slot}"

    @property
    def _target(self) -> dict[str, Any] | None:
        targets = self._client.target_list
        index = self._slot - 1
        if index >= len(targets):
            return None
        return targets[index]

    @property
    def native_value(self) -> str:
        target = self._target
        if target is None:
            return "not_detected"
        return "detected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        target = self._target
        if target is None:
            return {"slot": self._slot}
        return {
            "slot": self._slot,
            "target_id": target.get("id"),
            "x": target.get("x"),
            "y": target.get("y"),
            "z": target.get("z"),
            "minz": target.get("minz"),
            "maxz": target.get("maxz"),
            "timestamp": target.get("timestamp"),
        }
