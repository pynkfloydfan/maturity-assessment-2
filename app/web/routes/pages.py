from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.infrastructure.config import get_settings
from app.web.assets import get_frontend_assets

router = APIRouter(tags=["pages"])

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _base_context(request: Request) -> dict[str, object]:
    settings = get_settings()
    assets = get_frontend_assets()
    return {
        "request": request,
        "app_title": settings.app.title,
        "scripts": assets.get("scripts", []),
        "styles": assets.get("styles", []),
    }


@router.get("/", response_class=HTMLResponse)
async def spa_root(request: Request) -> HTMLResponse:
    context = _base_context(request)
    return templates.TemplateResponse("index.html", context)


@router.get("/{path:path}", response_class=HTMLResponse)
async def spa_catch_all(path: str, request: Request) -> HTMLResponse:
    context = _base_context(request)
    context["spa_path"] = path
    return templates.TemplateResponse("index.html", context)

