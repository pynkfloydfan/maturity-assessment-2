from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_server


@pytest.fixture
def tmp_frontend(tmp_path: Path) -> Path:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    return frontend


def test_ensure_frontend_build_triggers_npm(tmp_frontend: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_frontend.parent / "app" / "web" / "static" / "frontend" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(run_server, "FRONTEND_DIR", tmp_frontend)
    monkeypatch.setattr(run_server, "MANIFEST", manifest)

    calls: list[tuple[list[str], str]] = []

    def fake_run(cmd: list[str], cwd: str, check: bool) -> None:
        calls.append((cmd, cwd))

    monkeypatch.setattr(run_server.subprocess, "run", fake_run)

    run_server.ensure_frontend_build()

    assert calls, "npm commands were not invoked"
    assert calls[0][0] == ["npm", "install"]
    assert Path(calls[0][1]) == tmp_frontend
    assert calls[1][0] == ["npm", "run", "build"]
