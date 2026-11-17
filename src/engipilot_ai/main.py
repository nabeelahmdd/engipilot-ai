"""FastAPI application factory and lifecycle management."""

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import Response

import engipilot_ai.models  # noqa: F401
from engipilot_ai.api.health import router as health_router
from engipilot_ai.core.config import get_settings
from engipilot_ai.core.database import get_engine, get_session_factory
from engipilot_ai.core.db_base import Base


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield

    get_session_factory.cache_clear()

    if get_engine.cache_info().currsize:
        await get_engine().dispose()
        get_engine.cache_clear()


def create_app() -> FastAPI:
    # Validate all ORM relationships before handling requests.
    Base.registry.configure()

    settings = get_settings()

    logging.basicConfig(level=getattr(logging, settings.log_level))

    app = FastAPI(
        title="EngiPilot AI API",
        version="0.0.1",
        lifespan=lifespan,
        docs_url=("/docs" if settings.app_env in ("local", "test") else None),
        redoc_url=None,
    )

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[
            [Request],
            Awaitable[Response],
        ],
    ) -> Response:
        # Generate an internal correlation ID.
        correlation_id = str(uuid.uuid4())

        request.state.request_id = correlation_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = correlation_id

        return response

    app.include_router(
        health_router,
        prefix="/api/v1",
    )

    return app


app = create_app()
