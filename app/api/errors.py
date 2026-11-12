"""One error format for every API response, and the handlers that produce it.

    {"error": {"code": "invalid_url", "message": "...", "fields": [{"field": ..., "message": ...}]}}

`fields` appears only on validation errors. Pages outside /api keep their own handling.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..services.errors import ServiceError
from ..services.ratelimit import RateLimited

API_PREFIX = "/api/"

STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    503: "unavailable",
}


class FieldError(BaseModel):
    field: str
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_json(
    status: int,
    code: str,
    message: str,
    fields: list[FieldError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, fields=fields))
    return JSONResponse(body.model_dump(exclude_none=True), status_code=status, headers=headers)


def is_api(request: Request) -> bool:
    return request.url.path.startswith(API_PREFIX)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError) -> Response:
        return error_json(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RateLimited)
    async def rate_limited(request: Request, exc: RateLimited) -> Response:
        return error_json(
            429,
            "rate_limited",
            "Too many requests; slow down and try again shortly",
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> Response:
        fields = [
            FieldError(field=_field_name(err), message=str(err.get("msg", "Invalid value")))
            for err in exc.errors()
        ]
        if not is_api(request):
            return JSONResponse({"detail": [f.model_dump() for f in fields]}, 422)
        return error_json(422, "validation_error", "Request is invalid", fields)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        headers = dict(exc.headers) if exc.headers else None
        if not is_api(request):
            return JSONResponse({"detail": exc.detail}, exc.status_code, headers=headers)
        code = STATUS_CODES.get(exc.status_code, "error")
        return error_json(exc.status_code, code, str(exc.detail), headers=headers)


def _field_name(err: dict[str, Any]) -> str:
    # ("body", "url") -> "url"; ("query", "format") -> "format"
    loc = [str(part) for part in err.get("loc", ()) if part not in ("body", "query", "path")]
    return ".".join(loc) or "request"
