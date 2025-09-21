from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import uvicorn

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MANIFEST = Path(__file__).resolve().parent.parent / "app" / "web" / "static" / "frontend" / "manifest.json"


def ensure_frontend_build() -> None:
    if MANIFEST.exists():
        return

    if not FRONTEND_DIR.exists():
        print("[run-server] Frontend directory not found; skipping build.")
        return

    print("[run-server] Frontend assets missing. Running npm install & npm run build…")
    try:
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)
        subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "npm is not available on PATH. Install Node.js (which ships with npm) "
            "to build the frontend bundle."
        ) from exc


def main() -> None:
    try:
        ensure_frontend_build()
    except Exception as exc:  # pragma: no cover - developer helper
        print(f"[run-server] Warning: {exc}")

    uvicorn.run(
        "app.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
