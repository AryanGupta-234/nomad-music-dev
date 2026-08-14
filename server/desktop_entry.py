"""Production entrypoint for the NOMAD Music bundled local API sidecar."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def _default_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "NOMAD Music" / "data"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "nomad-music"


data_dir = Path(os.environ.get("NOMAD_DATA_DIR", _default_data_dir()))
data_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NOMAD_DATA_DIR", str(data_dir))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(data_dir / 'nomad.db').as_posix()}")
os.environ.setdefault("APP_ENV", "desktop")
os.environ.setdefault("PUBLIC_BASE_URL", "http://127.0.0.1:8765")

# The bundled executable receives the app package through PyInstaller.
# Add the server package directory to sys.path so `app.*` imports keep the
# same layout as development.
server_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

import uvicorn  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8765,
        log_level="info",
    )
