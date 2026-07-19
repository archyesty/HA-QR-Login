"""Authenticated WebSocket commands used by the approve panel.

This is the security core: approval only ever happens over an
authenticated WebSocket connection, so the approver's identity is the
session's identity — it cannot be spoofed from the car page.

Permission rules:
- approver must be an active, non-system user
- admins may always approve; any other user must be explicitly
  allowlisted in the integration options to approve even themselves
- minting for a DIFFERENT user requires the approver to be admin
  AND the cross-user option to be enabled
- non-admins can only ever mint for themselves
- the owner account can never be a cross-user target
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.persistent_notification import async_create
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_ALLOWED_USERS,
    CONF_CROSS_USER,
    DOMAIN,
    EVENT_APPROVED,
)
from .session_store import SessionStore


def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_list_users)
    websocket_api.async_register_command(hass, ws_approve)
    websocket_api.async_register_command(hass, ws_deny)
    websocket_api.async_register_command(hass, ws_session_info)


def _options(hass: HomeAssistant) -> dict:
    return hass.data[DOMAIN]["options"]


def _approver_allowed(hass: HomeAssistant, user) -> bool:
    if user is None or user.system_generated or not user.is_active:
        return False
    if user.is_admin:
        return True
    return user.id in _options(hass).get(CONF_ALLOWED_USERS, [])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/session_info", vol.Required("code"): str})
@callback
def ws_session_info(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Let the panel show the display code + expiry for verification."""
    store: SessionStore = hass.data[DOMAIN]["store"]
    session = store.get(msg["code"])
    if session is None:
        connection.send_error(msg["id"], "not_found", "Code expired or unknown")
        return
    connection.send_result(msg["id"], {"display": session.display, "status": session.status})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_users"})
@websocket_api.async_response
async def ws_list_users(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Users the approver may mint for. Non-admins only see themselves."""
    me = connection.user
    if not _approver_allowed(hass, me):
        connection.send_error(msg["id"], "unauthorized", "Not permitted to approve logins")
        return
    cross = _options(hass).get(CONF_CROSS_USER, True) and me.is_admin
    if cross:
        users = [
            {"id": u.id, "name": u.name, "is_admin": u.is_admin, "is_me": u.id == me.id}
            for u in await hass.auth.async_get_users()
            if u.is_active and not u.system_generated and not (u.is_owner and u.id != me.id)
        ]
    else:
        users = [{"id": me.id, "name": me.name, "is_admin": me.is_admin, "is_me": True}]
    connection.send_result(msg["id"], {"users": users})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/approve",
        vol.Required("code"): str,
        vol.Required("user_id"): str,
    }
)
@websocket_api.async_response
async def ws_approve(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    me = connection.user
    store: SessionStore = hass.data[DOMAIN]["store"]

    if not _approver_allowed(hass, me):
        connection.send_error(msg["id"], "unauthorized", "Not permitted to approve logins")
        return

    target = await hass.auth.async_get_user(msg["user_id"])
    if target is None or not target.is_active or target.system_generated:
        connection.send_error(msg["id"], "bad_target", "Invalid target user")
        return

    if target.id != me.id:
        if not (me.is_admin and _options(hass).get(CONF_CROSS_USER, True)):
            connection.send_error(msg["id"], "unauthorized", "Only admins may log in another user")
            return
        if target.is_owner:
            connection.send_error(msg["id"], "unauthorized", "Owner account cannot be a cross-user target")
            return

    session = store.get(msg["code"])
    if session is None:
        connection.send_error(msg["id"], "not_found", "Code expired — start again on the car")
        return

    # Mint fresh credentials for the target, at this moment.
    base_url = str(hass.config.external_url or hass.config.internal_url or "").rstrip("/")
    client_id = f"{base_url}/" if base_url else None
    refresh = await hass.auth.async_create_refresh_token(
        target,
        client_id=client_id,
        client_name=f"QR Login (approved by {me.name})",
    )
    access = hass.auth.async_create_access_token(refresh)
    expires_in = int(refresh.access_token_expiration.total_seconds())

    tokens = {
        "access_token": access,
        "refresh_token": refresh.token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "clientId": client_id,
        "hassUrl": base_url,
    }

    if not store.approve(msg["code"], tokens, me.name, target.name):
        # Session raced to expiry/denial: revoke what we just minted.
        hass.auth.async_remove_refresh_token(refresh)
        connection.send_error(msg["id"], "not_found", "Code expired — start again on the car")
        return

    hass.bus.async_fire(
        EVENT_APPROVED,
        {"approver": me.name, "target": target.name, "cross_user": target.id != me.id},
    )
    async_create(
        hass,
        f"{me.name} approved a QR login as **{target.name}**. "
        f"Revoke anytime from that user's profile (token: 'QR Login').",
        title="QR Login approved",
        notification_id=f"{DOMAIN}_{session.display}",
    )
    connection.send_result(msg["id"], {"ok": True, "target": target.name})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/deny", vol.Required("code"): str})
@callback
def ws_deny(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    store: SessionStore = hass.data[DOMAIN]["store"]
    store.deny(msg["code"])
    connection.send_result(msg["id"], {"ok": True})
