# Mobile Plan

NOMAD Music desktop is now the primary client and is a single Tauri `.exe` with a React/Vite WebView.

Mobile remains a future React Native/Expo client.

The mobile client must consume the same `/api/v1` contract and share:

- Track Graph
- playlists
- queue semantics
- recommendation engine
- provider sync state
- lyrics APIs
- analytics events

No recommendation/business logic should be duplicated inside mobile.
