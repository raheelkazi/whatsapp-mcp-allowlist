# whatsapp-mcp-server/tests/test_ratelimit.py
from ratelimit import RateLimiter


def test_first_send_allowed():
    rl = RateLimiter(min_interval_sec=3, max_per_hour=30)
    allowed, reason = rl.try_send(now=100.0)
    assert allowed is True and reason == ""


def test_rejects_within_min_interval():
    rl = RateLimiter(min_interval_sec=3, max_per_hour=30)
    rl.try_send(now=100.0)
    allowed, reason = rl.try_send(now=101.0)  # only 1s later
    assert allowed is False
    assert "min interval" in reason


def test_allows_after_min_interval():
    rl = RateLimiter(min_interval_sec=3, max_per_hour=30)
    rl.try_send(now=100.0)
    allowed, _ = rl.try_send(now=103.5)
    assert allowed is True


def test_rejects_over_hourly_cap():
    rl = RateLimiter(min_interval_sec=0, max_per_hour=2)
    assert rl.try_send(now=1.0)[0] is True
    assert rl.try_send(now=2.0)[0] is True
    allowed, reason = rl.try_send(now=3.0)
    assert allowed is False
    assert "hourly cap" in reason


def test_hourly_window_slides():
    rl = RateLimiter(min_interval_sec=0, max_per_hour=2)
    rl.try_send(now=1.0)
    rl.try_send(now=2.0)
    # 1 hour + later: the first two have aged out, so a new send is allowed
    allowed, _ = rl.try_send(now=3700.0)
    assert allowed is True


def test_rejected_send_does_not_consume_quota():
    rl = RateLimiter(min_interval_sec=3, max_per_hour=30)
    rl.try_send(now=100.0)
    rl.try_send(now=100.5)  # rejected (too soon)
    # the rejected attempt should not count toward the interval/quota state
    allowed, _ = rl.try_send(now=103.0)
    assert allowed is True
