import logging
from time import perf_counter
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def valid_request_id(value: str | None) -> str:
    if value is not None:
        try:
            parsed = UUID(value)
            if parsed.version == 4:
                return str(parsed)
        except ValueError:
            pass
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = perf_counter()
        request_id = valid_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        request.app.state.logger = logging.getLogger("healthsphere")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        request.app.state.logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return response
