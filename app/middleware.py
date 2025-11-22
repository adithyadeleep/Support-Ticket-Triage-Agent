import time
import asyncio
from collections import deque, defaultdict
from typing import Deque

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding-window rate limiter.
    Limits requests per IP to max_requests in window_seconds.
    """

    def __init__(self, app, max_requests: int = 20, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # mapping ip -> deque[timestamps]
        self._storage: dict[str, Deque[float]] = defaultdict(deque)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client = request.client
        ip = client.host if client else "unknown"

        now = time.time()
        dq = self._storage[ip]
        lock = self._locks[ip]

        async with lock:
            # drop old timestamps
            while dq and dq[0] <= now - self.window_seconds:
                dq.popleft()
            if len(dq) >= self.max_requests:
                # Too Many Requests
                retry_after = int(dq[0] + self.window_seconds - now) if dq else self.window_seconds
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later.", "retry_after": retry_after},
                    headers={"Retry-After": str(retry_after)}
                )
            dq.append(now)

        # proceed
        response = await call_next(request)
        return response
