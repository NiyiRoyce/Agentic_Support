# request logging middleware (stub)

"""Logging middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import time

from observability.metrics import increment_request_count, observe_request_duration

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""

    async def dispatch(self, request: Request, call_next):
        # Log request
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(f"Request: {request.method} {request.url.path} [{request_id}]")

        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} [{request_id}] ({duration:.3f}s)"
        )

        # Update metrics
        increment_request_count(request.method, request.url.path, response.status_code)
        observe_request_duration(request.method, request.url.path, duration)

        return response
