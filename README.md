# Home Assistant Explorer

Home Assistant Explorer is the backend custom integration for the Explorer floor-plan project.

## Current prototype

The first supported positioning source is **Shelly Presence Gen4** over the local network.

The integration:

- connects directly to the Shelly over local WebSocket RPC
- starts `Presence.LiveTrack`
- keeps live tracking active
- listens for `NotifyEvent` → `presence` → `track`
- exposes the current targets and their raw `id`, `x`, `y`, `z`, `minz` and `maxz` values in Home Assistant
- supports up to 10 target slots in the current prototype

No Shelly Cloud connection is required for live position data.

## Installation with HACS

Home Assistant Explorer can be installed as a custom HACS integration.

1. Open HACS in Home Assistant.
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/MVtag/ha-explorer`.
4. Select **Integration** as the category.
5. Install **Home Assistant Explorer**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration → Home Assistant Explorer**.
8. Enter the local IP address of the Shelly Presence Gen4.

During development, the repository can be installed from the default branch before the first tagged release. Tagged releases will use the version in `manifest.json`.

## Entities

The prototype creates:

- `Targets` — number of currently tracked radar targets, with the complete target list in attributes
- `Target 1` … `Target 10` — target slots with position attributes

A detected target exposes attributes similar to:

```text
target_id: 5
x: -0.38
y: 0.93
z: 0.04
minz: 1.76
maxz: 1.93
```

## Development validation

GitHub Actions validates the repository with both HACS validation and Home Assistant hassfest on pushes and pull requests.

## Next milestones

1. Verify live tracking on a real Home Assistant installation.
2. Add calibration from Shelly-local X/Y coordinates to Explorer floor-plan coordinates.
3. Add multiple Shelly Presence Gen4 sensors/rooms.
4. Add target hand-off between rooms.
5. Add person identity matching using BLE/device-presence signals.
6. Feed normalized live positions to `ha-explorer-card`.
