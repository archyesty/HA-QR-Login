"""In-memory store for pending QR login sessions.

Nothing is persisted to disk. Codes are 128-bit random, single use,
and expire after a short TTL. Tokens are only ever held between the
moment of approval and the first successful poll delivery.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from .const import STATUS_APPROVED, STATUS_DENIED, STATUS_PENDING

MAX_PENDING = 20  # global cap, keeps an attacker from filling memory


@dataclass
class Session:
    code: str
    display: str
    created: float
    status: str = STATUS_PENDING
    tokens: dict | None = None
    approver_name: str | None = None
    target_name: str | None = None
    delivered: bool = False
    peer_ip: str | None = None


@dataclass
class SessionStore:
    ttl: int
    _sessions: dict[str, Session] = field(default_factory=dict)

    def _purge(self) -> None:
        now = time.time()
        for code in [c for c, s in self._sessions.items() if now - s.created > self.ttl]:
            self._sessions.pop(code, None)

    def create(self, peer_ip: str | None) -> Session | None:
        self._purge()
        if len(self._sessions) >= MAX_PENDING:
            return None
        code = secrets.token_urlsafe(16)  # 128-bit
        display = code[-6:].upper().replace("_", "X").replace("-", "Z")
        session = Session(code=code, display=display, created=time.time(), peer_ip=peer_ip)
        self._sessions[code] = session
        return session

    def get(self, code: str) -> Session | None:
        self._purge()
        return self._sessions.get(code)

    def approve(self, code: str, tokens: dict, approver: str, target: str) -> bool:
        session = self.get(code)
        if session is None or session.status != STATUS_PENDING:
            return False
        session.status = STATUS_APPROVED
        session.tokens = tokens
        session.approver_name = approver
        session.target_name = target
        return True

    def deny(self, code: str) -> None:
        session = self.get(code)
        if session:
            session.status = STATUS_DENIED

    def deliver(self, code: str) -> dict | None:
        """Hand tokens to the poller exactly once, then destroy."""
        session = self.get(code)
        if session is None or session.status != STATUS_APPROVED or session.delivered:
            return None
        session.delivered = True
        tokens = session.tokens
        self._sessions.pop(code, None)
        return tokens
