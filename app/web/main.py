from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.infrastructure.config import get_settings
from app.web.assets import reset_manifest_cache
from app.web.routes import api, pages

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app.title,
        version=settings.app.version,
        debug=settings.app.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), check_dir=False), name="static")

    app.include_router(api.router)
    app.include_router(pages.router)

    @app.on_event("startup")
    async def startup_event() -> None:
        reset_manifest_cache()

    return app


app = create_application()

