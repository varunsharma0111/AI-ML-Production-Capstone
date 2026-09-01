"""Sliding-window rate-limiting middleware for abuse protection."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import DomainError

MAX_REQUESTS_PER_MINUTE = 120
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis/In-Memory sliding window rate limiter enforcing abuse limits."""

    def __init__(self, app: Any, requests_per_minute: int = MAX_REQUESTS_PER_MINUTE) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._local_buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Skip health check, metrics endpoints, and OPTIONS preflight requests
        if request.method == "OPTIONS" or request.url.path in (
            "/health/live",
            "/health/ready",
            "/api/v1/system/live",
            "/api/v1/system/status",
            "/metrics",
        ):
            return cast(Response, await call_next(request))

        # 1. Enforce payload size limit for upload requests
        if request.method in ("POST", "PUT") and "content-length" in request.headers:
            try:
                content_length = int(request.headers["content-length"])
                if content_length > MAX_UPLOAD_BYTES:
                    raise DomainError(
                        status_code=413,
                        code="payload_too_large",
                        title="Payload Too Large",
                        detail=(
                            "File upload size exceeds maximum"
                            f" limit of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
                        ),
                    )
            except ValueError:
                pass

        # 2. Extract rate limit key (user_id or client IP)
        client_ip = request.client.host if request.client else "unknown"
        user_key = f"rate_limit:{client_ip}"

        now = time.time()
        window_start = now - 60.0

        redis_mgr = getattr(request.app.state, "redis_manager", None)
        is_exceeded = False

        if redis_mgr and getattr(redis_mgr, "_redis", None):
            try:
                # Redis zset sliding window
                pipe = redis_mgr._redis.pipeline()
                pipe.zremrangebyscore(user_key, 0, window_start)
                pipe.zadd(user_key, {str(now): now})
                pipe.zcard(user_key)
                pipe.expire(user_key, 60)
                results = await pipe.execute()
                count = results[2]
                if count > self.requests_per_minute:
                    is_exceeded = True
            except Exception:
                # Fallback to local in-memory window
                is_exceeded = self._check_local_rate_limit(user_key, now, window_start)
        else:
            is_exceeded = self._check_local_rate_limit(user_key, now, window_start)

        if is_exceeded:
            raise DomainError(
                status_code=429,
                code="rate_limit_exceeded",
                title="Too Many Requests",
                detail="Rate limit exceeded. Please wait before retrying.",
            )

        return cast(Response, await call_next(request))

    def _check_local_rate_limit(self, key: str, now: float, window_start: float) -> bool:
        timestamps = [t for t in self._local_buckets[key] if t > window_start]
        timestamps.append(now)
        self._local_buckets[key] = timestamps
        return len(timestamps) > self.requests_per_minute
