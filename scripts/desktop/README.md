# Desktop build

NOMAD Music is a Tauri 2 desktop app with a bundled FastAPI sidecar.

## Windows release flow

1. Install Node 20+, Rust stable, WebView2, and Python 3.12+.
2. From the repository root run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\desktop\build-server.ps1
```

3. From `apps/desktop` install the Tauri CLI dependencies and build:

```powershell
npm install
npm run build
```

The resulting installer/bundle contains the `nomad-server` sidecar, so end users do not need Python, Node, or a manually launched backend.
