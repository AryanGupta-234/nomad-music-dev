#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../server"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..
mkdir -p data/cache data/logs data/backups
cp -n .env.example .env || true
echo "Dev environment ready."
