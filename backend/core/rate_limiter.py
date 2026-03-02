"""SlowAPI rate-limiter setup."""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import settings


def _get_identifier(request: Request) -> str:
    """Use the API key as the rate-limit bucket for external clients; IP for JWT users."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api:{api_key}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_identifier)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "retry_after": exc.detail},
    )


def user_limit() -> str:
    return f"{settings.RATE_LIMIT_USER}/minute"


def api_client_limit() -> str:
    return f"{settings.RATE_LIMIT_API_CLIENT}/minute"
