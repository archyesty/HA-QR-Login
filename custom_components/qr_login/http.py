"""Unauthenticated HTTP surface: the car page, session start, and polling."""
from __future__ import annotations

import time
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import API_BASE, CAR_PAGE_PATH, DOMAIN, STATUS_DENIED
from .session_store import SessionStore

FRONTEND_DIR = Path(__file__).parent / "frontend"

# Naive per-IP rate limit for the unauthenticated endpoints
_BUCKET: dict[str, list[float]] = {}
_LIMIT = 30          # requests
_WINDOW = 60.0       # per minute


def _rate_limited(request: web.Request) -> bool:
    ip = request.remote or "?"
    now = time.time()
    hits = [t for t in _BUCKET.get(ip, []) if now - t < _WINDOW]
    hits.append(now)
    _BUCKET[ip] = hits
    return len(hits) > _LIMIT


class CarPageView(HomeAssistantView):
    """Serves the static page the car opens. No auth by design."""

    url = CAR_PAGE_PATH
    name = f"{DOMAIN}:page"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        html = (FRONTEND_DIR / "car_page.html").read_text()
        return web.Response(text=html, content_type="text/html")


class StartView(HomeAssistantView):
    url = f"{API_BASE}/start"
    name = f"{DOMAIN}:start"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        if _rate_limited(request):
            return self.json({"error": "rate_limited"}, status_code=429)
        hass: HomeAssistant = request.app["hass"]
        store: SessionStore = hass.data[DOMAIN]["store"]
        session = store.create(request.remote)
        if session is None:
            return self.json({"error": "busy"}, status_code=503)
        return self.json({"code": session.code, "display": session.display, "ttl": store.ttl})


class PollView(HomeAssistantView):
    url = f"{API_BASE}/poll"
    name = f"{DOMAIN}:poll"
    requires_auth = False

    async def post(self, request: web.Request) -> web.Response:
        if _rate_limited(request):
            return self.json({"error": "rate_limited"}, status_code=429)
        hass: HomeAssistant = request.app["hass"]
        store: SessionStore = hass.data[DOMAIN]["store"]
        body = await request.json()
        code = str(body.get("code", ""))
        session = store.get(code)
        if session is None:
            return self.json({"status": "expired"})
        if session.status == STATUS_DENIED:
            return self.json({"status": "denied"})
        tokens = store.deliver(code)
        if tokens is None:
            return self.json({"status": "pending"})
        return self.json({"status": "approved", "tokens": tokens})
