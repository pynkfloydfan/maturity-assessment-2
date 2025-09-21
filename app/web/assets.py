from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
import json

BUILD_DIR = Path(__file__).resolve().parent / "static" / "frontend"
MANIFEST_CANDIDATES = [
    BUILD_DIR / "manifest.json",
    BUILD_DIR / ".vite" / "manifest.json",
]


@lru_cache(maxsize=1)
def load_manifest() -> Dict[str, Any]:
    for manifest_path in MANIFEST_CANDIDATES:
        if manifest_path.exists():
            try:
                return json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return {}


def get_frontend_assets() -> dict[str, List[str]]:
    manifest = load_manifest()
    if not manifest:
        # Fallback to dev mode placeholders; actual dev server handled separately
        return {
            "scripts": ["/static/frontend/main.js"],
            "styles": [],
        }

    entry = manifest.get("index.html")
    if not isinstance(entry, dict):
        return {"scripts": [], "styles": []}

    scripts: List[str] = []
    styles: List[str] = []

    entry_file = entry.get("file")
    if entry_file:
        scripts.append(f"/static/frontend/{entry_file}")

    for css in entry.get("css", []):
        styles.append(f"/static/frontend/{css}")

    for dynamic in entry.get("imports", []):
        chunk = manifest.get(dynamic)
        if isinstance(chunk, dict):
            file_path = chunk.get("file")
            if file_path:
                scripts.append(f"/static/frontend/{file_path}")
            for css in chunk.get("css", []):
                styles.append(f"/static/frontend/{css}")

    return {"scripts": scripts, "styles": styles}


def reset_manifest_cache() -> None:
    load_manifest.cache_clear()

