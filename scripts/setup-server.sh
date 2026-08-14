#!/usr/bin/env bash
set -euo pipefail
apt update
apt install -y git curl ffmpeg fpcalc sqlite3 python3 python3-venv python3-pip caddy
mkdir -p /opt/nomad-music
chown -R "$USER":"$USER" /opt/nomad-music
echo "Server packages installed. Clone/deploy NOMAD into /opt/nomad-music and configure .env."
