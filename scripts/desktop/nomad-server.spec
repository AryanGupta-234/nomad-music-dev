# PyInstaller spec for the local NOMAD Music FastAPI sidecar.
# The project root is injected by build-server.ps1 so this works reliably
# when PyInstaller executes the spec without a __file__ global.
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.environ.get("NOMAD_PROJECT_ROOT") or Path.cwd()).resolve()
SERVER = ROOT / "server"

if not SERVER.exists():
    raise RuntimeError(f"NOMAD server directory not found: {SERVER}")

# `pathex` belongs to the later Analysis phase; collect_submodules() runs
# while this spec itself is being evaluated, so make the package importable
# here as well.
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

hiddenimports = collect_submodules("app")
hiddenimports += [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
]

analysis = Analysis(
    [str(SERVER / "desktop_entry.py")],
    pathex=[str(SERVER)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="nomad-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
