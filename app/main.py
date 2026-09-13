from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    configure_logging(application_settings.log_level)

    app = FastAPI(
        title="HealthSphere Backend",
        version="0.1.0",
        debug=application_settings.debug,
    )
    app.state.settings = application_settings
    app.add_middleware(RequestContextMiddleware)
    if application_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(application_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Content-Type", "X-CSRF-Token", "X-Request-ID"],
        )
    install_exception_handlers(app)
    app.include_router(health_router)
    return app
