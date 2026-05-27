"""
Simple sliding-window rate limiter (no Redis needed).
Limits each user to MAX_REQUESTS per TIME_WINDOW seconds.
"""
from collections import defaultdict
from time import time

MAX_REQUESTS  = 10   # requests allowed
TIME_WINDOW   = 60   # per 60 seconds

# {user_id: [timestamp, timestamp, ...]}
_request_log: dict[str, list] = defaultdict(list)


def is_allowed(user_id: str) -> bool:
    """
    Returns True if request is within limits.
    Returns False if user has exceeded MAX_REQUESTS in the last TIME_WINDOW seconds.
    """
    now          = time()
    window_start = now - TIME_WINDOW

    # Drop timestamps outside the window
    _request_log[user_id] = [t for t in _request_log[user_id] if t > window_start]

    if len(_request_log[user_id]) >= MAX_REQUESTS:
        return False

    _request_log[user_id].append(now)
    return True


def seconds_until_reset(user_id: str) -> int:
    """How many seconds until the oldest request falls out of the window."""
    if not _request_log[user_id]:
        return 0
    oldest = min(_request_log[user_id])
    return max(0, int(TIME_WINDOW - (time() - oldest)) + 1)
