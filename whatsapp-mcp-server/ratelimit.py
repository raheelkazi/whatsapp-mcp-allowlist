# whatsapp-mcp-server/ratelimit.py
"""In-memory send rate limiter — enforces the anti-ban guidance.

Rejects (never queues) a send that comes too soon after the previous one or that
would exceed the hourly cap. State is per-process and resets on restart, which is
fine for the on-demand usage model.
"""
import os

DEFAULT_MIN_INTERVAL_SEC = 3.0
DEFAULT_MAX_PER_HOUR = 30


class RateLimiter:
    def __init__(self, min_interval_sec: float, max_per_hour: int):
        self.min_interval_sec = min_interval_sec
        self.max_per_hour = max_per_hour
        self._sends: list[float] = []  # timestamps of allowed sends

    def try_send(self, now: float) -> tuple[bool, str]:
        """Return (allowed, reason). Records the send only when allowed, so a
        rejected attempt does not consume quota."""
        self._sends = [t for t in self._sends if now - t < 3600]
        if self._sends and (now - self._sends[-1]) < self.min_interval_sec:
            wait = self.min_interval_sec - (now - self._sends[-1])
            return False, f"min interval {self.min_interval_sec}s not elapsed (wait {wait:.1f}s)"
        if len(self._sends) >= self.max_per_hour:
            return False, f"hourly cap of {self.max_per_hour} sends reached"
        self._sends.append(now)
        return True, ""


def from_env() -> RateLimiter:
    return RateLimiter(
        min_interval_sec=float(
            os.environ.get("WHATSAPP_SEND_MIN_INTERVAL_SEC", DEFAULT_MIN_INTERVAL_SEC)
        ),
        max_per_hour=int(
            os.environ.get("WHATSAPP_SEND_MAX_PER_HOUR", DEFAULT_MAX_PER_HOUR)
        ),
    )
