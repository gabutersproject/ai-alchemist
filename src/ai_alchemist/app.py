"""FastAPI application. The browser and the provider client stay in separate modules."""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_alchemist.config import default_config_path
from ai_alchemist.errors import LabError
from ai_alchemist.providers.base import ChatProvider
from ai_alchemist.providers.registry import build_provider
from ai_alchemist.routes import router

WEB_DIR = Path(__file__).resolve().parent / "web"


def create_app(
    config_path: Path | None = None,
    provider_factory: Callable[..., ChatProvider] | None = None,
) -> FastAPI:
    """Build the laboratory app. Tests pass a config path and a provider factory."""
    app = FastAPI(title="AI Alchemist", docs_url="/docs", redoc_url=None)
    app.state.config_path = default_config_path() if config_path is None else config_path
    app.state.provider_factory = provider_factory or build_provider
    app.include_router(router)

    @app.exception_handler(LabError)
    async def lab_error(_: Request, exc: LabError) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo `input`. A rejected token or host must not come back in the body.
        parts: list[str] = []
        for item in exc.errors():
            loc = [str(piece) for piece in item.get("loc", []) if piece != "body"]
            message = str(item.get("msg", "Invalid value"))
            if message.startswith("Value error, "):
                message = message[len("Value error, ") :]
            parts.append(f"{'.'.join(loc)}: {message}" if loc else message)
        return JSONResponse({"detail": "; ".join(parts) or "Invalid request."}, status_code=422)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app
