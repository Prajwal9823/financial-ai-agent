"""
Outbound-request throttling for yfinance calls.

Yahoo Finance aggressively rate-limits (HTTP 429) when multiple requests
arrive in a short window — and our own dashboard makes this worse by
firing several yfinance-backed calls in parallel per search (price,
profile, fundamentals, technicals all separately hit Yahoo). This module
provides two things every yfinance-calling tool function should use:

1. `yf_lock` — a process-wide lock that serializes ALL outbound Yahoo
   requests from this backend, so a single dashboard search can no longer
   fire 3+ simultaneous Yahoo requests and trip their burst limiter.
2. `with_retry()` — a decorator that retries a transient failure (429,
   the empty-JSON response Yahoo sends when blocking, or the
   currentTradingPeriod KeyError some yfinance versions raise when Yahoo
   returns incomplete data) a few times with exponential backoff + jitter
   before giving up.

This does not make Yahoo's rate limiting disappear — nothing on our side
can — but it substantially reduces how often you'll actually hit it
during normal use.
"""
from __future__ import annotations

import functools
import random
import threading
import time

from app.core.logging_config import get_logger

log = get_logger("core.rate_limiter")

# Every yfinance call in the codebase should be made while holding this
# lock, so outbound requests to Yahoo are serialized instead of bursting.
yf_lock = threading.Lock()

# Minimum gap enforced between the END of one Yahoo request and the START
# of the next, regardless of which tool triggered it.
_MIN_INTERVAL_SECONDS = 0.6
_last_request_at = 0.0
_interval_lock = threading.Lock()


def _throttle() -> None:
    global _last_request_at
    with _interval_lock:
        wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


_RETRYABLE_MESSAGES = ("429", "too many requests", "expecting value", "currenttradingperiod", "rate limit")


def _is_retryable(exc: Exception) -> bool:
    return any(m in str(exc).lower() for m in _RETRYABLE_MESSAGES)


def with_retry(max_attempts: int = 3, base_delay: float = 1.5):
    """Decorator: runs `fn` under the shared Yahoo throttle/lock, retrying
    transient rate-limit-shaped failures with exponential backoff + jitter."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                with yf_lock:
                    _throttle()
                    try:
                        return fn(*args, **kwargs)
                    except Exception as exc:  # noqa: BLE001 - broad on purpose, see _is_retryable
                        last_exc = exc
                        if not _is_retryable(exc) or attempt == max_attempts:
                            raise
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                log.warning(
                    f"[YF] {fn.__name__} hit a retryable error (attempt {attempt}/{max_attempts}): "
                    f"{last_exc} — retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            raise last_exc  # pragma: no cover - unreachable, loop always returns or raises above

        return wrapper

    return decorator
