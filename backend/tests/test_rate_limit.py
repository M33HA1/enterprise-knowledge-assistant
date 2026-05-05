from app.middleware import _check_rate_limit, _rate_limit_buckets


def test_rate_limit_blocks_after_limit():
    key = "test:/api/query:127.0.0.1"
    _rate_limit_buckets.pop(key, None)

    assert _check_rate_limit(key, limit=2, window_seconds=60) is True
    assert _check_rate_limit(key, limit=2, window_seconds=60) is True
    assert _check_rate_limit(key, limit=2, window_seconds=60) is False
