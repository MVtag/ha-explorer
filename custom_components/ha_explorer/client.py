"""Local Shelly Presence Gen4 client for Home Assistant Explorer."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import json
import logging
from typing import Any

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType

from .const import LIVE_TRACK_REFRESH_SECONDS, RECONNECT_DELAY_SECONDS

_LOGGER = logging.getLogger(__name__)


class ShellyPresenceError(Exception):
    """Base exception for Shelly Presence communication errors."""


class ShellyPresenceConnectionError(ShellyPresenceError):
    """Raised when a Shelly Presence device cannot be reached."""


class ShellyPresenceClient:
    """Maintain a local WebSocket connection to a Shelly Presence Gen4."""

    def __init__(self, session: ClientSession, host: str, source: str) -> None:
        """Initialize the client."""
        self._session = session
        self.host = host
        self.source = source
        self.targets: dict[int, dict[str, Any]] = {}
        self.connected = False
        self._listeners: set[Callable[[], None]] = set()
        self._runner_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._request_id = 0

    @property
    def target_list(self) -> list[dict[str, Any]]:
        """Return current targets sorted by Shelly target ID."""
        return [self.targets[key] for key in sorted(self.targets)]

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener and return an unsubscribe callback."""
        self._listeners.add(listener)

        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    async def async_start(self) -> None:
        """Start the WebSocket worker."""
        if self._runner_task is not None and not self._runner_task.done():
            return
        self._stop_event.clear()
        self._runner_task = asyncio.create_task(self._run(), name=f"ha_explorer_{self.host}")

    async def async_stop(self) -> None:
        """Stop the WebSocket worker."""
        self._stop_event.set()
        if self._runner_task is None:
            return
        self._runner_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._runner_task
        self._runner_task = None
        self.connected = False

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - reconnect worker must survive transport errors
                self.connected = False
                self.targets = {}
                self._notify_listeners()
                _LOGGER.warning("Shelly Presence connection to %s failed: %s", self.host, err)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=RECONNECT_DELAY_SECONDS)
                except TimeoutError:
                    pass

    async def _connect_and_listen(self) -> None:
        url = f"ws://{self.host}/rpc"
        async with self._session.ws_connect(url, heartbeat=30) as websocket:
            self.connected = True
            self._notify_listeners()
            _LOGGER.debug("Connected to Shelly Presence at %s", self.host)

            await self._send_live_track(websocket)
            refresh_task = asyncio.create_task(self._refresh_live_track(websocket))
            try:
                async for message in websocket:
                    if self._stop_event.is_set():
                        break
                    if message.type == WSMsgType.TEXT:
                        self._handle_message(message.data)
                    elif message.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.ERROR):
                        break
            finally:
                refresh_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await refresh_task
                self.connected = False
                self._notify_listeners()

    async def _refresh_live_track(self, websocket: ClientWebSocketResponse) -> None:
        while not self._stop_event.is_set() and not websocket.closed:
            await asyncio.sleep(LIVE_TRACK_REFRESH_SECONDS)
            if websocket.closed:
                return
            await self._send_live_track(websocket)

    async def _send_live_track(self, websocket: ClientWebSocketResponse) -> None:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "src": self.source,
            "method": "Presence.LiveTrack",
        }
        await websocket.send_json(payload)

    def _handle_message(self, raw_data: str) -> None:
        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError:
            _LOGGER.debug("Ignoring non-JSON Shelly WebSocket message: %s", raw_data)
            return

        if payload.get("method") != "NotifyEvent":
            return

        params = payload.get("params") or {}
        events = params.get("events") or []
        for event in events:
            if event.get("component") != "presence" or event.get("event") != "track":
                continue

            objects = event.get("object") or []
            next_targets: dict[int, dict[str, Any]] = {}
            for obj in objects:
                if not isinstance(obj, dict) or "id" not in obj:
                    continue
                try:
                    target_id = int(obj["id"])
                except (TypeError, ValueError):
                    continue
                next_targets[target_id] = {
                    "id": target_id,
                    "x": obj.get("x"),
                    "y": obj.get("y"),
                    "z": obj.get("z"),
                    "minz": obj.get("minz"),
                    "maxz": obj.get("maxz"),
                    "timestamp": event.get("ts", params.get("ts")),
                }

            self.targets = next_targets
            self._notify_listeners()


async def async_validate_shelly_presence(
    session: ClientSession, host: str
) -> dict[str, Any]:
    """Validate a Shelly Presence and return basic device information."""
    try:
        async with session.get(
            f"http://{host}/rpc/Shelly.GetDeviceInfo", timeout=10
        ) as response:
            response.raise_for_status()
            device_info = await response.json()

        async with session.get(
            f"http://{host}/rpc/Presence.GetStatus", timeout=10
        ) as response:
            response.raise_for_status()
            presence_status = await response.json()
    except Exception as err:  # noqa: BLE001 - normalized to integration exception
        raise ShellyPresenceConnectionError(str(err)) from err

    if "sensor_ver" not in presence_status:
        raise ShellyPresenceError("Device does not expose the Shelly Presence component")

    return {
        "device_id": device_info.get("id") or device_info.get("mac") or host,
        "model": device_info.get("model") or "Shelly Presence Gen4",
        "mac": device_info.get("mac"),
        "firmware": device_info.get("ver"),
    }
