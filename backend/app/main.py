
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine
from app.api.v1.router import api_router
from app.core.logging_config import configure_logging


configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered customer support SaaS platform.",
)

app.include_router(api_router)


def get_request_id(request: Request) -> str:
    """Return the request ID assigned by the middleware."""
    request_id = getattr(request.state, "request_id", None)

    if not request_id:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

    return request_id


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Request completed | request_id=%s method=%s "
        "path=%s status_code=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    response.headers["X-Request-ID"] = request_id

    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    request_id = get_request_id(request)

    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "Request failed"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": jsonable_encoder(exc.detail),
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
                "details": None,
                "request_id": request_id,
            },
        },
        headers={
            **(exc.headers or {}),
            "X-Request-ID": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    request_id = get_request_id(request)
    validation_errors = jsonable_encoder(exc.errors())

    return JSONResponse(
        status_code=422,
        content={
            "detail": validation_errors,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": validation_errors,
                "request_id": request_id,
            },
        },
        headers={
            "X-Request-ID": request_id,
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    request_id = get_request_id(request)

    logger.error(
        "Unhandled exception | request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "details": None,
                "request_id": request_id,
            },
        },
        headers={
            "X-Request-ID": request_id,
        },
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to SupportFlow AI API",
        "version": settings.app_version,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
    }


@app.get("/health/database", tags=["Health"])
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        logger.exception("Database health check failed")

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )
