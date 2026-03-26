from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        self._public_prefixes = (
            "/docs",
            "/openapi.json",
            "/redoc",
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith(self._public_prefixes):
            return await call_next(request)

        api_key = request.headers.get("x-api-key")
        if not api_key or api_key != self.settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing x-api-key"})

        return await call_next(request)
