# NOMAD Music — API Credentials

NOMAD Music can start without provider credentials. Real integrations are enabled later.

## Spotify

Create a Spotify Developer app and set the OAuth callback to:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

Provide:

```text
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

## YouTube / Google

Create a Google Cloud project, enable YouTube Data API v3, and configure an OAuth client.

Provide:

```text
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

## Optional

```text
GROQ_API_KEY=
LASTFM_API_KEY=
GENIUS_API_KEY=
ACOUSTID_API_KEY=
```

Never commit real keys into the repository.
