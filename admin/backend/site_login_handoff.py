from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from pilot.utils import normalize_host


@dataclass(frozen=True)
class SiteLoginHandoff:
    site: str
    host: str
    redirect_url: str
    secure: bool
    expires_at: float


@dataclass(frozen=True)
class IssuedSiteLoginHandoff:
    token: str
    handoff: SiteLoginHandoff


class SiteLoginHandoffStore:
    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        ttl_seconds: int = 60,
        capacity: int = 128,
    ) -> None:
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._handoffs: dict[str, SiteLoginHandoff] = {}
        self._lock = threading.Lock()

    def issue(
        self,
        site: str,
        redirect_url: str,
        *,
        host: str | None = None,
        secure: bool,
    ) -> IssuedSiteLoginHandoff:
        now = self._clock()
        handoff = SiteLoginHandoff(
            site=normalize_host(site),
            host=normalize_host(host or site),
            redirect_url=redirect_url,
            secure=secure,
            expires_at=now + self._ttl_seconds,
        )
        token = secrets.token_urlsafe(32)
        digest = self._digest(token)
        with self._lock:
            self._discard_expired(now)
            if len(self._handoffs) >= self._capacity:
                oldest = min(
                    self._handoffs,
                    key=lambda key: self._handoffs[key].expires_at,
                )
                self._handoffs.pop(oldest)
            self._handoffs[digest] = handoff
        return IssuedSiteLoginHandoff(token=token, handoff=handoff)

    def consume(self, token: str, host: str) -> SiteLoginHandoff | None:
        if not isinstance(token, str) or len(token) > 128:
            return None
        with self._lock:
            handoff = self._handoffs.pop(self._digest(token), None)
        if handoff is None:
            return None
        if handoff.expires_at < self._clock():
            return None
        if handoff.host != normalize_host(host):
            return None
        return handoff

    def _discard_expired(self, now: float) -> None:
        expired = [
            key
            for key, handoff in self._handoffs.items()
            if handoff.expires_at < now
        ]
        for key in expired:
            self._handoffs.pop(key)

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
