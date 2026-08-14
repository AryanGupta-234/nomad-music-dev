# Deployment

## Target

Small always-on Linux server. The application is designed to run as a single API process plus worker/scheduler processes, behind Caddy.

## Production processes

- nomad-api.service
- nomad-worker.service
- nomad-scheduler.service

## Data

- `/opt/nomad-music/data`
- daily SQLite backup
- persistent provider cache

## Reverse proxy

Caddy terminates TLS and forwards to FastAPI on localhost.
