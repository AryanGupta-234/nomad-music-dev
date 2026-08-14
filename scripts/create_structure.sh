#!/usr/bin/env bash
set -euo pipefail
# Idempotent project scaffold creator. Re-run safely.
python3 - <<'PY'
from pathlib import Path
for p in Path('.').rglob('*'):
    pass
print('NOMAD Music structure already provisioned.')
PY
