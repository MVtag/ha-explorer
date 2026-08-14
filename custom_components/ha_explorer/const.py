"""Constants for Home Assistant Explorer."""

DOMAIN = "ha_explorer"
PLATFORMS = ["sensor"]

CONF_DEVICE_ID = "device_id"
CONF_MODEL = "model"
CONF_MAP_X = "map_x"
CONF_MAP_Y = "map_y"
CONF_ROTATION = "rotation"

DEFAULT_NAME = "Home Assistant Explorer"
DEFAULT_MAP_X = 0.0
DEFAULT_MAP_Y = 0.0
DEFAULT_ROTATION = 0.0
MAX_TARGET_SLOTS = 10
LIVE_TRACK_REFRESH_SECONDS = 50
RECONNECT_DELAY_SECONDS = 5
