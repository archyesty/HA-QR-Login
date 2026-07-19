"""QR Login — device-code style login for Home Assistant.

A car/TV/kiosk opens /qr-login, shows a QR; a signed-in phone scans it,
approves (optionally choosing which user to log in), and the waiting
device receives freshly minted credentials. Nothing exists before
approval; codes are single-use and expire in ~60 seconds.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    async_remove_panel,
)
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import websocket
from .const import (
    API_BASE,
    APPROVE_PANEL_PATH,
    CONF_ALLOWED_USERS,
    CONF_CODE_TTL,
    CONF_CROSS_USER,
    DEFAULT_ALLOWED_USERS,
    DEFAULT_CODE_TTL,
    DEFAULT_CROSS_USER,
    DOMAIN,
)
from .http import CarPageView, PollView, StartView
from .session_store import SessionStore

FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    options = {
        CONF_CODE_TTL: entry.options.get(CONF_CODE_TTL, DEFAULT_CODE_TTL),
        CONF_CROSS_USER: entry.options.get(CONF_CROSS_USER, DEFAULT_CROSS_USER),
        CONF_ALLOWED_USERS: entry.options.get(CONF_ALLOWED_USERS, DEFAULT_ALLOWED_USERS),
    }
    hass.data[DOMAIN] = {
        "store": SessionStore(ttl=options[CONF_CODE_TTL]),
        "options": options,
    }

    hass.http.register_view(CarPageView())
    hass.http.register_view(StartView())
    hass.http.register_view(PollView())

    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"{API_BASE}/panel.js", str(FRONTEND_DIR / "panel.js"), False)]
    )

    websocket.async_register(hass)

    async_register_built_in_panel(
        hass,
        component_name="custom",
        frontend_url_path=APPROVE_PANEL_PATH,
        require_admin=False,
        config={
            "_panel_custom": {
                "name": "qr-approve-panel",
                "module_url": f"{API_BASE}/panel.js",
                "embed_iframe": False,
            }
        },
    )

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    async_remove_panel(hass, APPROVE_PANEL_PATH)
    hass.data.pop(DOMAIN, None)
    return True
