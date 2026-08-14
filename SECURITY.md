# Security Baseline

- Secrets only in environment or secret manager.
- Never expose provider client secrets to clients.
- Validate OAuth state.
- Prefer PKCE for clients where secrets cannot be protected.
- HTTPS in production.
- CORS allowlist.
- Rate-limit public endpoints.
- Timeouts around all provider calls.
- Never trust external provider metadata as safe HTML.
- Back up the SQLite database.
