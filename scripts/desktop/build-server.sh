#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python -m pip install -r server/requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm scripts/desktop/nomad-server.spec
mkdir -p apps/desktop/src-tauri/binaries
TRIPLE="$(rustc -vV | awk '/host:/{print $2}')"
case "$TRIPLE" in
  x86_64-pc-windows-msvc) cp dist/nomad-server.exe "apps/desktop/src-tauri/binaries/nomad-server-${TRIPLE}.exe" ;;
  *) cp dist/nomad-server "apps/desktop/src-tauri/binaries/nomad-server-${TRIPLE}" ;;
esac
echo "Bundled sidecar for $TRIPLE"
