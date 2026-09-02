"""Minimal in-process rate limiting for the authentication endpoints.

Deliberately dependency-free and in-process: it blunts credential-stuffing and
signup-abuse bursts against a single API worker. It is NOT a distributed
limiter -- each worker or replica keeps its own counters, so a production
deployment should also rate-limit at the edge (load balancer / WAF / API
gateway). The client is identified by its socket address, not by a
client-supplied header such as X-Forwarded-For, which callers can spoof; run
uvicorn with --proxy-headers behind a trusted proxy so that address is correct.
"""

from __future__ import annotations

import threading
import time

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window request counter keyed by client identity."""

    def __init__(self, max_requests: int, window_seconds: float):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record one attempt for `key`, raising HTTP 429 once the window is full."""
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            recent = [moment for moment in self._hits.get(key, []) if moment > cutoff]
            if len(recent) >= self._max_requests:
                self._hits[key] = recent
                retry_after = max(1, int(self._window_seconds - (now - recent[0])) + 1)
                raise HTTPException(
                    status_code=429,
                    detail="Too many attempts. Please wait and try again.",
                    headers={"Retry-After": str(retry_after)},
                )

            recent.append(now)
            self._hits[key] = recent
            self._prune(cutoff)

    def _prune(self, cutoff: float) -> None:
        """Drop keys whose whole window has expired so memory stays bounded."""
        expired = [key for key, moments in self._hits.items() if not moments or moments[-1] <= cutoff]
        for key in expired:
            del self._hits[key]

    def reset(self) -> None:
        """Clear all counters (used by tests)."""
        with self._lock:
            self._hits.clear()


def client_key(request: Request) -> str:
    """Identify the caller by socket address, falling back to a shared bucket."""
    client = request.client
    return client.host if client else "unknown"
