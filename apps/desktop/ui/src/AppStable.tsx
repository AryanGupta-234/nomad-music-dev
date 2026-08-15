import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

type Source = {
  provider: string;
  provider_id: string;
  playback_kind?: string | null;
  uri?: string | null;
};

type Track = {
  id: string;
  title: string;
  artist_name?: string | null;
  album_name?: string | null;
  duration_ms?: number | null;
  artwork_url?: string | null;
  sources?: Source[];
};

type Provider = {
  name: string;
  configured: boolean;
  mode?: string;
  connected?: boolean;
  account_name?: string | null;
};

type Queue = {
  current_item_id: string | null;
  is_playing: boolean;
  position_ms: number;
  volume: number;
  items: Array<{ id: string; track_id: string; position: number }>;
};

const API = import.meta.env.VITE_NOMAD_API || "http://127.0.0.1:8765/api/v1";

const ICONS: Record<string, string> = {
  home: "⌂",
  search: "⌕",
  discover: "✦",
  library: "♫",
  ai: "◉",
  play: "▶",
  pause: "Ⅱ",
  prev: "|◀",
  next: "▶|",
  queue: "☷",
  sync: "↻",
};

const icon = (name: string) => ICONS[name] || "•";
const artist = (track: Track) => track.artist_name || "Unknown artist";
const time = (ms?: number | null) => {
  if (ms == null) return "—";
  return `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;
};

export default function AppStable() {
  const [page, setPage] = useState("Home");
  const [library, setLibrary] = useState<Track[]>([]);
  const [results, setResults] = useState<Track[]>([]);
  const [recs, setRecs] = useState<Track[]>([]);
  const [radio, setRadio] = useState<Track[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [now, setNow] = useState<Track | null>(null);
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const [sources, setSources] = useState(false);
  const [youtubeId, setYoutubeId] = useState<string | null>(null);
  const [artError, setArtError] = useState<Record<string, boolean>>({});

  const audio = useRef<HTMLAudioElement | null>(null);
  const yt = useRef<HTMLIFrameElement | null>(null);
  const connections = useMemo(
    () => new Map(providers.map((provider) => [provider.name, provider])),
    [providers],
  );
  const youtubeConnected = Boolean(connections.get("youtube")?.connected);

  const flash = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2800);
  };

  async function api(path: string, init?: RequestInit): Promise<any> {
    const response = await fetch(API + path, init);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  async function refresh() {
    const [libraryData, recommendationData, connectionData, queueData] = await Promise.all([
      api("/library?limit=300").catch(() => ({ tracks: [] })),
      api("/recommendations?limit=30").catch(() => ({ results: [] })),
      api("/integrations/connections").catch(() => ({ connections: [] })),
      api("/player/queue").catch(() => null),
    ]);

    const tracks: Track[] = libraryData.tracks || [];
    setLibrary(tracks);

    const trackMap = new Map(tracks.map((track) => [track.id, track]));
    const recommended = (recommendationData.results || [])
      .map((item: { track_id: string }) => trackMap.get(item.track_id))
      .filter((track: Track | undefined): track is Track => Boolean(track));

    setRecs(recommended);
    setProviders(connectionData.connections || []);
    setQueue(queueData);
  }

  useEffect(() => {
    void refresh().catch((error) => flash(error instanceof Error ? error.message : "Refresh failed"));
  }, []);

  useEffect(() => {
    if (youtubeConnected && library.length === 0) {
      void syncYouTube();
    }
  }, [youtubeConnected]);

  async function syncYouTube() {
    if (!youtubeConnected) return;
    try {
      await api("/integrations/youtube/sync", { method: "POST" });
      await refresh();
      flash("YouTube library synced into the NOMAD graph.");
    } catch (error) {
      flash(error instanceof Error ? error.message : "YouTube sync failed");
    }
  }

  async function search() {
    if (!query.trim()) return;
    try {
      const data = await api(`/search?q=${encodeURIComponent(query)}&limit=40`);
      setResults((data.results || []).map((item: { track: Track }) => item.track));
      setPage("Search");
    } catch (error) {
      flash(error instanceof Error ? error.message : "Search failed");
    }
  }

  function youtubeCommand(func: string) {
    yt.current?.contentWindow?.postMessage(
      JSON.stringify({ event: "command", func, args: [] }),
      "https://www.youtube.com",
    );
  }

  async function play(track: Track) {
    try {
      const preferred = youtubeConnected ? "youtube" : undefined;
      const suffix = preferred ? `?preferred_source=${preferred}` : "";
      const data = await api(`/tracks/${track.id}/resolve${suffix}`);
      setNow(track);

      await api("/player/queue?start_index=0", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([track.id]),
      }).catch(() => undefined);

      if (data.provider === "youtube" && data.source) {
        setYoutubeId(String(data.source));
        flash("Playing with the official YouTube player.");
      } else if (data.provider === "local") {
        const player = audio.current || new Audio();
        audio.current = player;
        player.src = `${API}/tracks/${track.id}/audio`;
        player.volume = queue?.volume ?? 0.8;
        await player.play();
        await api("/player/state?is_playing=true", { method: "PATCH" }).catch(() => undefined);
      } else if (data.provider === "spotify") {
        flash("Spotify metadata is ready; playback needs a connected Spotify session.");
      } else {
        flash("Metadata found, but no direct playable source is available for this track.");
      }

      await refresh();
    } catch (error) {
      flash(error instanceof Error ? error.message : "Playback failed");
    }
  }

  async function startRadio() {
    try {
      const suffix = now ? `&seed_track_id=${encodeURIComponent(now.id)}` : "";
      const data = await api(`/radio?limit=20${suffix}`);
      setRadio(data.tracks || []);
      setPage("Discover");
      flash("Smart Radio generated.");
    } catch (error) {
      flash(error instanceof Error ? error.message : "Radio failed");
    }
  }

  async function next() {
    try {
      const data = await api("/player/next", { method: "POST" });
      setQueue(data);
      const item = data?.current_item_id
        ? data.items?.find((entry: { id: string }) => entry.id === data.current_item_id)
        : null;
      const trackId = item?.track_id;
      const track =
        library.find((item) => item.id === trackId) ||
        recs.find((item) => item.id === trackId) ||
        radio.find((item) => item.id === trackId);
      if (track) await play(track);
    } catch {
      // Keep the player quiet if the queue is empty.
    }
  }

  function artwork(track: Track, small = false) {
    const failed = artError[track.id];
    return track.artwork_url && !failed ? (
      <img
        className={small ? "ns-art-img ns-art-img-small" : "ns-art-img"}
        src={track.artwork_url}
        alt=""
        loading="lazy"
        onError={() => setArtError((current) => ({ ...current, [track.id]: true }))}
      />
    ) : (
      <span className="ns-art-fallback">N</span>
    );
  }

  function card(track: Track) {
    return (
      <button className="ns-card" key={track.id} onClick={() => void play(track)}>
        <div className="ns-cover">
          {artwork(track)}
          <i>{icon("play")}</i>
        </div>
        <b>{track.title}</b>
        <small>{artist(track)}</small>
      </button>
    );
  }

  const nav: Array<[string, string]> = [
    ["Home", "home"],
    ["Search", "search"],
    ["Discover", "discover"],
    ["Library", "library"],
    ["AI / Vibe", "ai"],
  ];

  function home() {
    return (
      <div className="ns-content">
        <section className="ns-hero">
          <div>
            <label>NOMAD MUSIC INTELLIGENCE</label>
            <h2>
              Music that feels
              <br />
              <em>specifically yours.</em>
            </h2>
            <p>Your provider graph, local library and listening signals in one lightweight workspace.</p>
            <div className="ns-actions">
              <button className="ns-primary" onClick={() => setPage("Discover")}>Explore for you</button>
              <button className="ns-secondary" onClick={() => setPage("Library")}>Your library</button>
            </div>
          </div>
          <div className="ns-stat">
            <strong>{recs.length || "—"}</strong>
            <span>live recommendations</span>
            <small>{youtubeConnected ? "YouTube connected" : "Connect a provider to personalize"}</small>
          </div>
        </section>
        <Rail title="Continue listening" items={library.slice(0, 8)} card={card} />
        <Rail title="Made for you" items={recs.slice(0, 10)} card={card} />
      </div>
    );
  }

  function discover() {
    return (
      <div className="ns-content">
        <header className="ns-section-head">
          <div>
            <label>PERSONALIZED</label>
            <h2>Discover</h2>
            <p>Recommendations are ranked from your actual library signals.</p>
          </div>
          <button className="ns-secondary" onClick={() => void startRadio()}>✦ Start Radio</button>
        </header>
        <Rail title="Made for you" items={recs} card={card} empty="Sync your connected library to build recommendations." />
        <Rail title="Smart Radio" items={radio} card={card} empty="Start Radio to generate a flow." />
      </div>
    );
  }

  function libraryPage() {
    return (
      <div className="ns-content">
        <header className="ns-section-head">
          <div>
            <label>YOUR MUSIC GRAPH</label>
            <h2>Library</h2>
            <p>{library.length} indexed tracks · Spotify/YouTube/Deezer/Apple metadata can coexist.</p>
          </div>
          <button className="ns-secondary" disabled={!youtubeConnected} onClick={() => void syncYouTube()}>
            {icon("sync")} Sync YouTube
          </button>
        </header>
        <div className="ns-list">
          {library.map((track, index) => (
            <div className="ns-row" key={track.id}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div className="ns-row-art">{artwork(track, true)}</div>
              <div className="ns-row-main">
                <b>{track.title}</b>
                <small>{artist(track)}{track.album_name ? ` · ${track.album_name}` : ""}</small>
              </div>
              <small className="ns-sources">
                {[...new Set((track.sources || []).map((source) => source.provider))].slice(0, 3).join(" · ")}
              </small>
              <small>{time(track.duration_ms)}</small>
              <button onClick={() => void play(track)}>{icon("play")}</button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function searchPage() {
    return (
      <div className="ns-content">
        <header className="ns-section-head">
          <div>
            <label>FEDERATED SEARCH</label>
            <h2>Results</h2>
            <p>{results.length} matches across the provider graph.</p>
          </div>
        </header>
        <div className="ns-list">
          {results.map((track, index) => (
            <div className="ns-row" key={`${track.id}-${index}`}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div className="ns-row-art">{artwork(track, true)}</div>
              <div className="ns-row-main">
                <b>{track.title}</b>
                <small>{artist(track)}{track.album_name ? ` · ${track.album_name}` : ""}</small>
              </div>
              <small className="ns-sources">
                {[...new Set((track.sources || []).map((source) => source.provider))].join(" · ")}
              </small>
              <button onClick={() => void play(track)}>{icon("play")}</button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  function ai() {
    return (
      <div className="ns-content">
        <section className="ns-ai">
          <label>NOMAD AI</label>
          <h2>Ask for a vibe.</h2>
          <p>AI interprets intent; deterministic ranking chooses the music.</p>
          <input
            defaultValue="dark cinematic night drive, more discovery"
            onKeyDown={async (event) => {
              if (event.key !== "Enter") return;
              try {
                const data = await api(`/vibe?q=${encodeURIComponent(event.currentTarget.value)}`);
                flash(`Vibe parsed: ${JSON.stringify(data.query)}`);
              } catch (error) {
                flash(error instanceof Error ? error.message : "Vibe request failed");
              }
            }}
          />
          <div>
            <button onClick={() => void startRadio()}>Like this → Radio</button>
            <button onClick={() => setPage("Discover")}>Show my taste</button>
          </div>
        </section>
      </div>
    );
  }

  let body: ReactNode = home();
  if (page === "Discover") body = discover();
  if (page === "Library") body = libraryPage();
  if (page === "Search") body = searchPage();
  if (page === "AI / Vibe") body = ai();

  return (
    <div className="nomad-stable">
      <aside className="ns-side">
        <div className="ns-brand">
          <strong>N</strong>
          <div><b>NOMAD</b><small>MUSIC INTELLIGENCE</small></div>
        </div>
        <div className="ns-engine"><i /> LOCAL ENGINE <b>ONLINE</b></div>
        <nav>
          {nav.map(([id, iconName]) => (
            <button key={id} className={page === id ? "active" : ""} onClick={() => setPage(id)}>
              <span>{icon(iconName)}</span>
              {id}
              {id === "Discover" && recs.length > 0 ? <em>{recs.length}</em> : null}
            </button>
          ))}
        </nav>
        <div className="ns-side-bottom">
          <button onClick={() => setSources(true)}>
            <b>● Source Hub</b>
            <small>{providers.filter((p) => p.configured).length} configured · {providers.filter((p) => p.connected).length} connected</small>
          </button>
          <small>NOMAD · STABLE</small>
        </div>
      </aside>

      <main className="ns-main">
        <header className="ns-top">
          <div>
            <label>{page === "Home" ? "GOOD EVENING" : page.toUpperCase()}</label>
            <h1>{page === "Home" ? "Aryan" : page}</h1>
          </div>
          <div className="ns-search">
            <span>{icon("search")}</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => { if (event.key === "Enter") void search(); }}
              placeholder="Search songs, artists, albums…"
            />
            <kbd>Enter</kbd>
          </div>
        </header>
        {notice ? <div className="ns-notice">{notice}</div> : null}
        {body}
      </main>

      <footer className="ns-player">
        <div className="ns-now">
          {now ? (
            <>
              <div className="ns-now-art">{artwork(now, true)}</div>
              <div><b>{now.title}</b><small>{artist(now)}</small></div>
            </>
          ) : <small>Choose a track to start listening</small>}
        </div>
        <div className="ns-controls">
          <button onClick={() => void api("/player/previous", { method: "POST" }).then(setQueue)}>{icon("prev")}</button>
          <button
            className="ns-play"
            onClick={() => {
              if (youtubeId) {
                const playing = Boolean(queue?.is_playing);
                youtubeCommand(playing ? "pauseVideo" : "playVideo");
                setQueue((current) => current ? { ...current, is_playing: !playing } : current);
              } else if (audio.current) {
                if (audio.current.paused) void audio.current.play();
                else audio.current.pause();
              }
            }}
          >{icon(queue?.is_playing ? "pause" : "play")}</button>
          <button onClick={() => void next()}>{icon("next")}</button>
        </div>
        <div className="ns-player-right">
          <span>{youtubeId ? "YouTube" : "NOMAD"}</span>
          <button onClick={() => flash(`${queue?.items.length || 0} queued`)}>{icon("queue")}</button>
        </div>
      </footer>

      {youtubeId ? (
        <div className="ns-youtube" aria-label="YouTube playback">
          <iframe
            ref={yt}
            title="YouTube playback"
            allow="autoplay; encrypted-media; picture-in-picture"
            src={`https://www.youtube.com/embed/${encodeURIComponent(youtubeId)}?enablejsapi=1&autoplay=1&playsinline=1&origin=${encodeURIComponent(window.location.origin)}`}
            onLoad={() => window.setTimeout(() => youtubeCommand("playVideo"), 250)}
          />
        </div>
      ) : null}

      {sources ? (
        <div className="ns-overlay" onClick={() => setSources(false)}>
          <section className="ns-modal" onClick={(event) => event.stopPropagation()}>
            <div className="ns-modal-head">
              <div><label>SOURCE HUB</label><h3>Provider status</h3></div>
              <button onClick={() => setSources(false)}>×</button>
            </div>
            {providers.map((provider) => (
              <div className="ns-provider" key={provider.name}>
                <i className={provider.connected ? "good" : provider.configured ? "ready" : "off"} />
                <b>{provider.name}</b>
                <small>
                  {provider.connected
                    ? `Connected${provider.account_name ? ` · ${provider.account_name}` : ""}`
                    : provider.mode === "public_metadata" ? "Public metadata" : "Configured / not connected"}
                </small>
              </div>
            ))}
            <p>
              Spotify is used for catalog and metadata when configured. YouTube OAuth powers your library sync;
              playback uses the official embedded YouTube player. Deezer and Apple remain federated metadata sources.
            </p>
          </section>
        </div>
      ) : null}
    </div>
  );
}

function Rail({
  title,
  items,
  card,
  empty,
}: {
  title: string;
  items: Track[];
  card: (track: Track) => ReactNode;
  empty?: string;
}) {
  return (
    <section className="ns-rail">
      <div className="ns-rail-head"><h3>{title}</h3><span>{items.length}</span></div>
      {items.length ? <div className="ns-grid">{items.map(card)}</div> : <div className="ns-empty">{empty || "Nothing here yet."}</div>}
    </section>
  );
}
