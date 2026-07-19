"""Config flow for QR Login (single instance + options)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ALLOWED_USERS,
    CONF_CODE_TTL,
    CONF_CROSS_USER,
    DEFAULT_ALLOWED_USERS,
    DEFAULT_CODE_TTL,
    DEFAULT_CROSS_USER,
    DOMAIN,
)

DOCS_URL = "https://github.com/archyesty/HA-QR-Login"


class QRLoginConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="QR Login", data={})
        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "docs": f"[Documentation & security model]({DOCS_URL})"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return QRLoginOptionsFlow()


class QRLoginOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        opts = self.config_entry.options

        # Admins are always permitted; only non-admin users are offered
        # for allowlisting, and unlisted non-admins cannot approve at all.
        users = await self.hass.auth.async_get_users()
        choices = {
            u.id: u.name
            for u in users
            if u.is_active and not u.system_generated and not u.is_admin
        }
        # Keep previously-allowlisted users selectable even if renamed/demoted oddly
        for uid in opts.get(CONF_ALLOWED_USERS, []):
            choices.setdefault(uid, uid)

        return self.async_show_form(
            step_id="init",
            description_placeholders={"docs": f"[Documentation]({DOCS_URL})"},
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CODE_TTL, default=opts.get(CONF_CODE_TTL, DEFAULT_CODE_TTL)
                    ): vol.All(int, vol.Range(min=30, max=300)),
                    vol.Required(
                        CONF_CROSS_USER, default=opts.get(CONF_CROSS_USER, DEFAULT_CROSS_USER)
                    ): bool,
                    vol.Optional(
                        CONF_ALLOWED_USERS,
                        default=opts.get(CONF_ALLOWED_USERS, DEFAULT_ALLOWED_USERS),
                    ): cv.multi_select(choices),
                }
            ),
        )
