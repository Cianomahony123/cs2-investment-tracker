import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request

_store: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def rate_limit(request: Request, max_calls: int, window: int) -> None:
    ip = (request.client.host if request.client else "unknown")
    now = time.time()
    cutoff = now - window
    with _lock:
        _store[ip] = [t for t in _store[ip] if t > cutoff]
        if len(_store[ip]) >= max_calls:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_calls} requests per {window}s.",
            )
        _store[ip].append(now)
