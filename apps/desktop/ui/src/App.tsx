import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

type Source = { provider: string; provider_id: string; playback_kind?: string | null; uri?: string | null; available?: boolean };
type Track = { id: string; title: string; artist_name?: string | null; album_name?: string | null; duration_ms?: number | null; artwork_url?: string | null; artist_id?: string | null; sources?: Source[] };
type Playlist = { id: string; name: string; description?: string | null; artwork_url?: string | null; tracks: Track[] };
type QueueState = { current_item_id: string | null; is_playing: boolean; position_ms: number; volume: number; shuffle: boolean; repeat: string; items: {id:string;track_id:string;position:number;source?:string|null}[] };
type LyricLine = { time_ms: number; text: string };
type Provider = { name: string; configured: boolean; mode: string; connected?: boolean; authenticated?: boolean; account_name?: string | null };

const API = import.meta.env.VITE_NOMAD_API || "http://127.0.0.1:8765/api/v1";
const NAV = [
  { id: "Home", icon: "⌂", label: "Home" },
  { id: "Search", icon: "⌕", label: "Search" },
  { id: "Discover", icon: "✦", label: "Discover" },
  { id: "Library", icon: "♫", label: "Your Library" },
  { id: "Playlists", icon: "▣", label: "Playlists" },
  { id: "AI / Vibe", icon: "◉", label: "NOMAD AI" },
];
const fmtTime = (ms = 0) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;

export default function App() {
  const [active, setActive] = useState("Home");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Track[]>([]);
  const [library, setLibrary] = useState<Track[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [recommendations, setRecommendations] = useState<{ track_id: string; score: number; reason: Record<string, number> }[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [vibe, setVibe] = useState("dark cinematic night drive, more discovery");
  const [vibeResult, setVibeResult] = useState<Record<string, unknown> | null>(null);
  const [radio, setRadio] = useState<Track[]>([]);
  const [journey, setJourney] = useState<Track[]>([]);
  const [nowPlaying, setNowPlaying] = useState<Track | null>(null);
  const [resolution, setResolution] = useState<{provider?:string;kind?:string;source?:string;reason?:string} | null>(null);
  const [queue, setQueue] = useState<QueueState | null>(null);
  const [activePlaylist, setActivePlaylist] = useState<Playlist | null>(null);
  const [playlistDoctor, setPlaylistDoctor] = useState<{duplicate_count:number;missing?:string[];repeated_artists?:number;energy_jumps?:number;issues?:string[]} | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [lyrics, setLyrics] = useState<{found:boolean; plain:string; synced:string; source?:string|null; offset_ms?:number; lines?:LyricLine[]}>({found:false,plain:"",synced:""});
  const [activeLyric, setActiveLyric] = useState(-1);
  const [showLyrics, setShowLyrics] = useState(false);
  const [showQueue, setShowQueue] = useState(false);
  const [showConnections, setShowConnections] = useState(false);
  const [localRoot, setLocalRoot] = useState("");
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [liked, setLiked] = useState(false);
  const [searchFocus, setSearchFocus] = useState(false);
  const [newPlaylistOpen, setNewPlaylistOpen] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [newPlaylistDescription, setNewPlaylistDescription] = useState("");
  const [isExpandedPlayer, setIsExpandedPlayer] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);

  const recMap = useMemo(() => new Map(library.map((t) => [t.id, t])), [library]);
  const currentQueue = queue?.items || [];
  const connectionMap = useMemo(() => new Map(providers.map(p => [p.name, p])), [providers]);

  function flash(text: string) { setToast(text); window.setTimeout(() => setToast(""), 2300); }
  function artistOf(t?: Track | null) { return t?.artist_name || "Unknown artist"; }
  function artStyle(t?: Track | null) { return t?.artwork_url ? { backgroundImage: `url(${t.artwork_url})` } : undefined; }
  function providerState(name: string) {
    const p = connectionMap.get(name);
    if (!p) return { label: "Unavailable", tone: "muted" };
    if (p.connected || p.authenticated) return { label: p.account_name ? `Connected · ${p.account_name}` : "Connected", tone: "good" };
    if (p.configured) return { label: p.mode === "public_metadata" ? "Ready" : "Ready to connect", tone: "ready" };
    return { label: "Not connected", tone: "muted" };
  }

  async function refresh() {
    const [lib, pls, rec, health, q, conns] = await Promise.all([
      fetch(`${API}/library?limit=100`).then(r => r.json()),
      fetch(`${API}/playlists`).then(r => r.json()),
      fetch(`${API}/recommendations?limit=12`).then(r => r.json()),
      fetch(`${API}/health/providers`).then(r => r.json()),
      fetch(`${API}/player/queue`).then(r => r.json()).catch(() => null),
      fetch(`${API}/integrations/connections`).then(r => r.json()).catch(() => ({ connections: [] })),
    ]);
    const combined = (conns.connections || []).map((c: Provider) => ({ ...(health.providers || []).find((p: Provider) => p.name === c.name), ...c }));
    setLibrary(lib.tracks || []);
    setPlaylists(Array.isArray(pls) ? pls : []);
    setRecommendations(rec.results || []);
    setProviders(combined.length ? combined : (health.providers || []));
    setQueue(q);
  }

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const d = await fetch(`${API}/search?q=${encodeURIComponent(query)}&limit=30`).then(r => r.json());
      setResults((d.results || []).map((x: { track: Track }) => x.track));
      setActive("Search");
    } finally { setBusy(false); }
  }

  async function syncSearch() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      await fetch(`${API}/search/sync?query=${encodeURIComponent(query)}&limit=24`, { method: "POST" });
      await refresh(); await search(); flash("Fresh provider results merged into your NOMAD graph.");
    } finally { setBusy(false); }
  }

  async function connect(provider: string) {
    try {
      const d = await fetch(`${API}/integrations/${provider}/authorize`).then(r => r.json());
      if (!d.authorization_url) throw new Error(d.detail || "Unable to start authorization");
      window.open(d.authorization_url, "_blank", "noopener,noreferrer");
      flash(`${provider[0].toUpperCase()}${provider.slice(1)} authorization opened.`);
    } catch (e) { flash(e instanceof Error ? e.message : "Could not open connection flow"); }
  }

  async function indexLocalLibrary() {
    if (!localRoot.trim()) return flash("Choose your Music folder first.");
    setBusy(true);
    try {
      const d = await fetch(`${API}/library/index?root=${encodeURIComponent(localRoot)}&recursive=true&limit=1000`, { method: "POST" }).then(r => r.json());
      if (!d.ok) throw new Error(d.detail || d.error || "Indexing failed");
      await refresh();
      flash(`Indexed ${d.indexed} new local track${d.indexed === 1 ? "" : "s"}.`);
    } catch (e) { flash(e instanceof Error ? e.message : "Could not index folder"); }
    finally { setBusy(false); }
  }

  async function loadLyrics(trackId: string, open = true) {
    try {
      const d = await fetch(`${API}/tracks/${trackId}/lyrics`).then(r => r.json());
      setLyrics({ ...d, lines: d.lines || [] });
      setActiveLyric(-1);
      if (open) setShowLyrics(true);
    } catch { setLyrics({ found: false, plain: "", synced: "", lines: [] }); if (open) setShowLyrics(true); }
  }

  async function favorite(track: Track) {
    const next = !liked;
    setLiked(next);
    await fetch(`${API}/tracks/${track.id}/favorite?liked=${next}`, { method: "POST" });
    flash(next ? "Added to Liked Songs" : "Removed from Likes");
  }

  async function startLocalPlayback(track: Track) {
    const local = (track.sources || []).find(s => s.provider === "local" && s.playback_kind === "local_audio");
    if (!local) return false;
    const audio = audioRef.current || new Audio();
    audioRef.current = audio;
    audio.src = `${API}/tracks/${track.id}/audio`;
    audio.preload = "auto";
    audio.volume = queue?.volume ?? 0.8;
    audio.onended = () => void control("next");
    audio.ontimeupdate = () => {
      const ms = audio.currentTime * 1000;
      setPosition(ms);
      const lines = lyrics.lines || [];
      let lo = 0, hi = lines.length - 1, best = -1;
      const target = ms + (lyrics.offset_ms || 0);
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (lines[mid].time_ms <= target) { best = mid; lo = mid + 1; } else hi = mid - 1;
      }
      setActiveLyric(best);
    };
    audio.onloadedmetadata = () => setDuration(audio.duration * 1000);
    await audio.play();
    setNowPlaying(track);
    setResolution({ provider: "local", kind: "local_audio", source: audio.src });
    const d = await fetch(`${API}/player/state?is_playing=true`, { method: "PATCH" }).then(r => r.json()).catch(() => null);
    if (d) setQueue(d);
    return true;
  }

  async function resolveAndQueue(track: Track, append = false) {
    setBusy(true);
    try {
      const ids = append ? [...(queue?.items || []).map(x => x.track_id), track.id] : [track.id];
      await fetch(`${API}/player/queue?start_index=${Math.max(0, ids.length - 1)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(ids) });
      const d = await fetch(`${API}/tracks/${track.id}/resolve`).then(r => r.json());
      setResolution(d); setNowPlaying(track); setLiked(false);
      if (d.available) {
        const played = await playResolvedTrack(track, d);
        if (!played) flash(`${d.provider} found a source, but playback needs the connected session.`);
      } else flash("NOMAD couldn't resolve a playable source yet.");
      await loadLyrics(track.id, false);
      const q = await fetch(`${API}/player/queue`).then(r => r.json()).catch(() => null); setQueue(q);
    } finally { setBusy(false); }
  }

  async function control(action: "next" | "previous") {
    const d = await fetch(`${API}/player/${action}`, { method: "POST" }).then(r => r.json());
    setQueue(d);
    const id = d?.current_item_id ? d.items?.find((x: { id: string; track_id: string }) => x.id === d.current_item_id)?.track_id : null;
    const t = (id && (library.find(x => x.id === id) || results.find(x => x.id === id) || radio.find(x => x.id === id) || journey.find(x => x.id === id))) || null;
    if (t) await resolveAndQueue(t, true);
  }

  async function togglePlayback() {
    const audio = audioRef.current;
    if (audio && resolution?.provider === "local") {
      if (audio.paused) await audio.play(); else audio.pause();
      const next = !audio.paused;
      const d = await fetch(`${API}/player/state?is_playing=${next}&position_ms=${Math.round(audio.currentTime * 1000)}`, { method: "PATCH" }).then(r => r.json()).catch(() => null);
      if (d) setQueue(d);
      return;
    }
    if (queue) {
      const d = await fetch(`${API}/player/state?is_playing=${!queue.is_playing}`, { method: "PATCH" }).then(r => r.json());
      setQueue(d);
    }
  }

  async function seekLocal(ms: number) {
    const audio = audioRef.current; if (!audio) return;
    audio.currentTime = Math.max(0, ms / 1000); setPosition(ms);
    await fetch(`${API}/player/state?position_ms=${Math.round(ms)}`, { method: "PATCH" }).catch(() => undefined);
  }

  async function setVolume(value: number) {
    const v = Math.max(0, Math.min(1, value));
    if (audioRef.current) audioRef.current.volume = v;
    const d = await fetch(`${API}/player/state?volume=${v}`, { method: "PATCH" }).then(r => r.json()).catch(() => null);
    if (d) setQueue(d);
  }

  async function playResolvedTrack(track: Track, resolved: any) {
    if (resolved?.provider === "local") return startLocalPlayback(track);
    if (resolved?.provider === "spotify" && resolved?.source) {
      const w = window as typeof window & { Spotify?: any; onSpotifyWebPlaybackSDKReady?: () => void };
      try {
        if (!w.Spotify) {
          await new Promise<void>((resolve, reject) => {
            const handler = () => { previous?.(); resolve(); };
            const previous = w.onSpotifyWebPlaybackSDKReady;
            w.onSpotifyWebPlaybackSDKReady = handler;
            const script = document.createElement("script"); script.src = "https://sdk.scdn.co/spotify-player.js"; script.onerror = () => reject(new Error("Spotify SDK unavailable")); document.head.appendChild(script);
          });
        }
        const token = await fetch(`${API}/integrations/spotify/player-token`).then(r => r.json());
        if (!token.access_token) throw new Error("Spotify isn't connected");
        const player = new w.Spotify.Player({ name: "NOMAD Music", getOAuthToken: (cb: any) => cb(token.access_token), volume: queue?.volume ?? 0.8 });
        let deviceId = "";
        await new Promise<void>((resolve, reject) => {
          let settled = false;
          const finish = (fn: () => void) => { if (settled) return; settled = true; fn(); };
          player.addListener("ready", ({ device_id }: any) => { deviceId = device_id; finish(resolve); });
          player.addListener("initialization_error", ({ message }: any) => finish(() => reject(new Error(message))));
          player.connect();
        });
        if (!deviceId) throw new Error("Spotify device unavailable");
        await fetch(`https://api.spotify.com/v1/me/player/play?device_id=${encodeURIComponent(deviceId)}`, { method: "PUT", headers: { Authorization: `Bearer ${token.access_token}`, "Content-Type": "application/json" }, body: JSON.stringify({ uris: [resolved.source] }) });
        setResolution(resolved); setNowPlaying(track); flash("Spotify playback connected");
        return true;
      } catch (e) { flash(e instanceof Error ? e.message : "Spotify playback unavailable"); }
    }
    if (resolved?.provider === "youtube" && resolved?.source) {
      const id = resolved.source.includes("v=") ? resolved.source.split("v=")[1].split("&")[0] : resolved.source;
      const url = `https://www.youtube.com/watch?v=${id}`;
      window.open(url, "_blank", "noopener,noreferrer");
      setResolution({ ...resolved, source: url }); setNowPlaying(track); flash("Opened YouTube playback source.");
      return true;
    }
    return false;
  }

  async function loadRadio(seed?: string) {
    const d = await fetch(`${API}/radio?limit=18${seed ? `&seed_track_id=${encodeURIComponent(seed)}` : ""}`).then(r => r.json());
    const map = new Map(library.map(t => [t.id, t]));
    setRadio((d.tracks || []).map((x: { id: string }) => map.get(x.id)).filter(Boolean) as Track[]); setActive("Discover");
  }

  async function loadJourney() {
    const d = await fetch(`${API}/vibe/journey?target_minutes=45&limit=24`).then(r => r.json());
    const map = new Map(library.map(t => [t.id, t]));
    setJourney((d.tracks || []).map((x: { id: string }) => map.get(x.id)).filter(Boolean) as Track[]); setActive("Discover");
  }

  async function interpretVibe() { const d = await fetch(`${API}/vibe?q=${encodeURIComponent(vibe)}`).then(r => r.json()); setVibeResult(d.query || null); setActive("AI / Vibe"); }

  async function openPlaylist(p: Playlist) {
    setActivePlaylist(p); setActive("Playlists");
    try { setPlaylistDoctor(await fetch(`${API}/playlists/${p.id}/doctor`).then(r => r.json())); } catch { setPlaylistDoctor(null); }
  }

  async function createPlaylist() {
    if (!newPlaylistName.trim()) return flash("Give the playlist a name.");
    const d = await fetch(`${API}/playlists`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newPlaylistName.trim(), description: newPlaylistDescription.trim() }) }).then(r => r.json());
    setNewPlaylistOpen(false); setNewPlaylistName(""); setNewPlaylistDescription(""); await refresh(); if (d?.id) flash("Playlist created.");
  }

  useEffect(() => { refresh().catch(() => undefined); }, []);
  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); searchRef.current?.focus(); } };
    window.addEventListener("keydown", fn); return () => window.removeEventListener("keydown", fn);
  }, []);

  return <main className="nomad-app">
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark"><span>N</span><i /></div>
        <div><div className="brand-name">NOMAD</div><div className="brand-sub">MUSIC INTELLIGENCE</div></div>
      </div>
      <div className="engine-chip"><span className="live-dot" /> Local engine <b>ONLINE</b></div>
      <div className="nav-section"><span>DISCOVER</span>{NAV.slice(0,3).map(item => <button className={`nav-item ${active === item.id ? "active" : ""}`} key={item.id} onClick={() => { setActive(item.id); setActivePlaylist(null); }}><span className="nav-icon">{item.icon}</span>{item.label}</button>)}</div>
      <div className="nav-section"><span>YOUR MUSIC</span>{NAV.slice(3,5).map(item => <button className={`nav-item ${active === item.id ? "active" : ""}`} key={item.id} onClick={() => { setActive(item.id); setActivePlaylist(null); }}><span className="nav-icon">{item.icon}</span>{item.label}</button>)}</div>
      <div className="nav-section"><span>NOMAD</span><button className={`nav-item ${active === "AI / Vibe" ? "active" : ""}`} onClick={() => { setActive("AI / Vibe"); setActivePlaylist(null); }}><span className="nav-icon">◉</span>NOMAD AI <em>NEW</em></button></div>
      <div className="sidebar-spacer" />
      <button className="connection-card" onClick={() => setShowConnections(true)}>
        <div className="connection-title">SOURCE HUB <span>›</span></div>
        <div className="connection-mini-row"><Dot state={providerState("spotify").tone} /><span>Spotify</span><small>{providerState("spotify").label}</small></div>
        <div className="connection-mini-row"><Dot state={providerState("youtube").tone} /><span>YouTube</span><small>{providerState("youtube").label}</small></div>
      </button>
      <div className="sidebar-foot">LOCAL-FIRST · DESKTOP · TEST BUILD</div>
    </aside>

    <section className="main-shell">
      <header className="topbar">
        <div className="page-heading"><div className="eyebrow">NOMAD MUSIC</div><h1>{active === "Home" ? "Good evening" : active === "AI / Vibe" ? "NOMAD Intelligence" : active}</h1><p>{active === "Home" ? "A music space that remembers, adapts and keeps moving." : subtitleFor(active)}</p></div>
        <div className={`global-search ${searchFocus ? "focus" : ""}`}>
          <span>⌕</span><input ref={searchRef} value={query} onFocus={() => setSearchFocus(true)} onBlur={() => setSearchFocus(false)} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()} placeholder="Search songs, artists, albums, playlists…"/><kbd>Ctrl K</kbd><button onClick={search}>{busy ? "…" : "Search"}</button>
        </div>
      </header>

      {toast && <div className="toast"><span className="toast-pulse" />{toast}</div>}

      {active === "Home" && <HomeView library={library} recommendations={recommendations} recMap={recMap} nowPlaying={nowPlaying} artistOf={artistOf} resolveAndQueue={resolveAndQueue} setActive={setActive} loadRadio={loadRadio} loadJourney={loadJourney} setShowConnections={setShowConnections} providers={providers} />}

      {active === "Search" && <section className="page-stack"><div className="section-head"><div><div className="eyebrow">UNIFIED SEARCH</div><h2>Everything, one graph.</h2><p>Search your indexed library first, then refresh external sources without leaving the page.</p></div><button className="outline-button" onClick={syncSearch}>↻ Refresh sources</button></div><div className="results-count">{results.length ? `${results.length} results` : "Search across your music graph"}</div><div className="track-table">{results.length ? results.map((t, i) => <TrackRow key={t.id} t={t} index={i + 1} onPlay={resolveAndQueue} onLyrics={() => loadLyrics(t.id)} />) : <EmptyState icon="⌕" title="Search your music" text="Try an artist, track, album, playlist or a natural-language request like “dark late-night electronic”." />}</div></section>}

      {active === "Library" && <section className="page-stack"><div className="section-head"><div><div className="eyebrow">YOUR LIBRARY</div><h2>Everything you keep.</h2><p>One canonical library across local files and connected providers.</p></div><div className="library-actions"><input value={localRoot} onChange={e => setLocalRoot(e.target.value)} placeholder="C:\\Music"/><button className="primary-button" disabled={busy} onClick={indexLocalLibrary}>Index folder</button></div></div><div className="stats-row"><Stat label="Tracks" value={library.length.toLocaleString()} /><Stat label="Artists" value={new Set(library.map(artistOf)).size.toLocaleString()} /><Stat label="Playlists" value={playlists.length.toLocaleString()} /><Stat label="Sources" value={`${new Set(library.flatMap(t => (t.sources || []).map(s => s.provider))).size}`} /></div><div className="track-table">{library.length ? library.map((t, i) => <TrackRow key={t.id} t={t} index={i + 1} onPlay={resolveAndQueue} onLyrics={() => loadLyrics(t.id)} />) : <EmptyState icon="♫" title="Your library is ready" text="Point NOMAD at your Music folder, then it will build the canonical graph automatically." />}</div></section>}

      {active === "Discover" && <DiscoverView radio={radio} journey={journey} nowPlaying={nowPlaying} onPlay={resolveAndQueue} loadRadio={loadRadio} loadJourney={loadJourney} />}

      {active === "Playlists" && <PlaylistView playlists={playlists} activePlaylist={activePlaylist} doctor={playlistDoctor} openPlaylist={openPlaylist} back={() => setActivePlaylist(null)} onPlay={resolveAndQueue} create={() => setNewPlaylistOpen(true)} />}

      {active === "AI / Vibe" && <AIView vibe={vibe} setVibe={setVibe} vibeResult={vibeResult} interpret={interpretVibe} journey={loadJourney} radio={() => loadRadio(nowPlaying?.id)} />}
    </section>

    {showLyrics && <LyricsDrawer track={nowPlaying} lyrics={lyrics} activeLyric={activeLyric} onClose={() => setShowLyrics(false)} onSeek={seekLocal} />}
    {showQueue && <QueueDrawer queue={queue} library={library} results={results} radio={radio} journey={journey} onClose={() => setShowQueue(false)} onPlay={resolveAndQueue} />}
    {showConnections && <ConnectionsModal providers={providers} onClose={() => setShowConnections(false)} onConnect={connect} />}
    {newPlaylistOpen && <CreatePlaylistModal name={newPlaylistName} description={newPlaylistDescription} setName={setNewPlaylistName} setDescription={setNewPlaylistDescription} onCancel={() => setNewPlaylistOpen(false)} onCreate={createPlaylist} />}

    <footer className={`now-playing ${isExpandedPlayer ? "expanded" : ""}`}>
      <button className="np-art" onClick={() => nowPlaying && setIsExpandedPlayer(v => !v)}><div className="art-fill" style={artStyle(nowPlaying)} /></button>
      <div className="np-main"><strong>{nowPlaying?.title || "Choose something to play"}</strong><span>{nowPlaying ? `${artistOf(nowPlaying)} · ${resolution?.provider || "resolving"}` : "NOMAD Music"}</span></div>
      <div className="np-actions"><button className={liked ? "liked" : ""} onClick={() => nowPlaying && favorite(nowPlaying)}>{liked ? "♥" : "♡"}</button><button onClick={() => nowPlaying && loadLyrics(nowPlaying.id)}>Lyrics</button></div>
      <div className="np-controls"><button onClick={() => control("previous")}>◀</button><button className="np-play" onClick={togglePlayback}>{queue?.is_playing ? "Ⅱ" : "▶"}</button><button onClick={() => control("next")}>▶</button></div>
      <div className="np-progress"><input type="range" min="0" max={Math.max(1, duration)} value={Math.min(position, duration || 1)} onChange={e => seekLocal(Number(e.target.value))}/><div><span>{fmtTime(position)}</span><span>{fmtTime(duration)}</span></div></div>
      <div className="np-end"><label>🔊<input type="range" min="0" max="1" step="0.01" value={queue?.volume ?? 0.8} onChange={e => setVolume(Number(e.target.value))}/></label><button onClick={() => setShowQueue(v => !v)} className="queue-button">Queue <b>{queue?.items?.length || 0}</b></button></div>
      {isExpandedPlayer && <div className="expanded-player"><div className="expanded-art" style={artStyle(nowPlaying)} /><div><div className="eyebrow">NOW PLAYING</div><h2>{nowPlaying?.title || "Nothing playing"}</h2><p>{nowPlaying ? artistOf(nowPlaying) : ""}</p><div className="expanded-actions"><button className="primary-button" onClick={() => nowPlaying && loadLyrics(nowPlaying.id)}>Open Lyrics</button><button className="outline-button" onClick={() => setShowQueue(true)}>Open Queue</button></div></div></div>}
    </footer>
  </main>;
}

function subtitleFor(active: string) {
  const map: Record<string,string> = { Search: "Find anything in your unified music graph.", Discover: "Follow the mood, not the algorithmic feed.", Library: "Your music, normalized across every source.", Playlists: "Intent, sequence and flow — not downloaded files.", "AI / Vibe": "Describe the moment. NOMAD handles the music intelligence." };
  return map[active] || "Your music, understood.";
}

function Dot({ state }: { state: string }) { return <i className={`status-led ${state}`} />; }
function Stat({label,value}:{label:string;value:string}) { return <div className="stat"><span>{label}</span><strong>{value}</strong></div>; }

function HomeView({library,recommendations,recMap,nowPlaying,artistOf,resolveAndQueue,setActive,loadRadio,loadJourney,setShowConnections,providers}:{library:Track[];recommendations:{track_id:string;score:number;reason:Record<string,number>}[];recMap:Map<string,Track>;nowPlaying:Track|null;artistOf:(t?:Track|null)=>string;resolveAndQueue:(t:Track,a?:boolean)=>void;setActive:(s:string)=>void;loadRadio:(id?:string)=>void;loadJourney:()=>void;setShowConnections:(v:boolean)=>void;providers:Provider[]}) {
  const recent = library.slice(0, 6);
  const top = recommendations.slice(0, 5).map(r => recMap.get(r.track_id)).filter(Boolean) as Track[];
  return <section className="page-stack home-page">
    <section className="home-hero-new">
      <div className="hero-copy-new"><div className="eyebrow">PERSONAL MUSIC INTELLIGENCE</div><h2>Music that feels<br /><em>specifically yours.</em></h2><p>NOMAD unifies your library, providers and listening signals into one graph — then turns that context into better music.</p><div className="hero-actions"><button className="primary-button" onClick={() => setActive("Discover")}>Explore for you</button><button className="outline-button" onClick={() => loadRadio(nowPlaying?.id)}>Start Smart Radio</button><button className="ghost-button" onClick={loadJourney}>Build a Vibe Journey</button></div><div className="hero-trust"><span><Dot state="good" /> Local engine online</span><span>{providers.filter(p => p.configured).length} sources available</span><button onClick={() => setShowConnections(true)}>Manage connections →</button></div></div>
      <div className="hero-art-stage"><div className="hero-orbit one" /><div className="hero-orbit two" /><div className="hero-art-stack"><div className="hero-art-card c1" style={artStyle(recent[0])}/><div className="hero-art-card c2" style={artStyle(recent[1])}/><div className="hero-art-card c3" style={artStyle(recent[2])}/></div><div className="hero-core">N</div><div className="hero-caption"><span>YOUR VIBE</span><strong>{nowPlaying ? `Around ${artistOf(nowPlaying)}` : "Building your taste profile"}</strong></div></div>
    </section>
    <div className="rail-head"><div><div className="eyebrow">CONTINUE LISTENING</div><h3>Pick up where you left off</h3></div><button onClick={() => setActive("Library")}>View library →</button></div>
    <div className="cover-rail">{recent.slice(0,5).map((t,idx)=><button className="music-card" key={t.id} onClick={() => resolveAndQueue(t)}><div className="music-card-art" style={artStyle(t)}><span className="card-play">▶</span></div><strong>{t.title}</strong><span>{artistOf(t)}</span>{idx===0&&<small>LAST PLAYED</small>}</button>)}</div>
    <section className="home-grid">
      <div className="surface large"><div className="surface-head"><div><div className="eyebrow">MADE FOR YOU</div><h3>Recommendations with reasons.</h3></div><button onClick={() => setActive("Discover")}>See all →</button></div><div className="mini-list">{recommendations.slice(0,6).map(r=>{const t=recMap.get(r.track_id); return t ? <TrackRow key={r.track_id} t={t} compact index={undefined} meta={`${Math.round(r.score*100)}% fit`} onPlay={resolveAndQueue} /> : null;})}</div></div>
      <div className="surface"><div className="surface-head"><div><div className="eyebrow">YOUR VIBE</div><h3>Right now</h3></div></div><div className="vibe-card"><div className="vibe-pulse"/><strong>{nowPlaying ? artistOf(nowPlaying) : "Start listening"}</strong><span>{nowPlaying ? "NOMAD is using this session as your current context." : "Your taste profile will sharpen as you listen."}</span><button onClick={loadJourney}>Turn it into a journey →</button></div></div>
    </section>
    <section className="surface"><div className="surface-head"><div><div className="eyebrow">FRESH DISCOVERY</div><h3>Things worth hearing next.</h3></div><button onClick={() => setActive("Search")}>Search more →</button></div><div className="discover-strip">{top.length ? top.slice(0,5).map(t => <button key={t.id} className="discover-tile" onClick={() => resolveAndQueue(t)}><div style={artStyle(t)} /><span>{artistOf(t)}</span><strong>{t.title}</strong></button>) : <EmptyState compact icon="✦" title="Your discovery shelf is warming up" text="Listen, like and save a few tracks and NOMAD will start filling this space." />}</div></section>
  </section>;
}

function DiscoverView({radio,journey,nowPlaying,onPlay,loadRadio,loadJourney}:{radio:Track[];journey:Track[];nowPlaying:Track|null;onPlay:(t:Track)=>void;loadRadio:(seed?:string)=>void;loadJourney:()=>void}) {
  return <section className="page-stack"><div className="discover-hero"><div><div className="eyebrow">DISCOVERY ENGINE</div><h2>Follow the feeling.</h2><p>Smart Radio stays close to the current track. Vibe Journey shapes a full session from calm to peak to cooldown.</p></div><div className="journey-meter"><span>ENERGY CURVE</span><div><i/><i/><i/><i/><i/><i/><i/><i/></div><small>prepared locally · adaptive</small></div></div><section className="feature-grid"><div className="surface feature"><div className="surface-head"><div><div className="eyebrow">SMART RADIO</div><h3>Never hit the dead end.</h3></div><button onClick={() => loadRadio(nowPlaying?.id)}>Generate</button></div>{radio.length ? <div className="mini-list">{radio.map((t,i) => <TrackRow key={`${t.id}-${i}`} t={t} compact meta={i < 3 ? "strong fit" : "radio candidate"} onPlay={onPlay}/>)}</div> : <EmptyState icon="◉" title="Build a radio from this moment" text="NOMAD will use the current track, taste and recent context." />}</div><div className="surface feature"><div className="surface-head"><div><div className="eyebrow">VIBE JOURNEY</div><h3>Let the set breathe.</h3></div><button onClick={loadJourney}>Build 45 min</button></div>{journey.length ? <div className="mini-list">{journey.slice(0,8).map((t,i) => <TrackRow key={`${t.id}-${i}`} t={t} compact meta={`chapter ${i+1}`} onPlay={onPlay}/>)}</div> : <EmptyState icon="↗" title="Shape an energy curve" text="Calm → groove → peak → cooldown, sequenced from your graph." />}</div></section></section>;
}

function PlaylistView({playlists,activePlaylist,doctor,openPlaylist,back,onPlay,create}:{playlists:Playlist[];activePlaylist:Playlist|null;doctor:any;openPlaylist:(p:Playlist)=>void;back:()=>void;onPlay:(t:Track)=>void;create:()=>void}) {
  if (activePlaylist) return <section className="page-stack"><button className="back-link" onClick={back}>← All playlists</button><section className="playlist-hero"><div className="playlist-cover" style={activePlaylist.artwork_url ? {backgroundImage:`url(${activePlaylist.artwork_url})`} : undefined}><span>♫</span></div><div className="playlist-info"><div className="eyebrow">PLAYLIST · {activePlaylist.tracks.length} TRACKS</div><h2>{activePlaylist.name}</h2><p>{activePlaylist.description || "A NOMAD playlist shaped by your taste and intent."}</p><div className="playlist-buttons"><button className="primary-button" onClick={() => activePlaylist.tracks[0] && onPlay(activePlaylist.tracks[0])}>▶ Play</button><button className="outline-button">↗ Flow</button><button className="outline-button">✨ Refine with AI</button></div></div></section><div className="playlist-intel-grid"><div className="intel-box accent"><span>PLAYLIST DNA</span><strong>Adaptive</strong><small>energy · mood · artist diversity</small></div><div className="intel-box"><span>FLOW</span><strong>Ready</strong><small>smart sequencing available</small></div><div className="intel-box"><span>DOCTOR</span><strong>{doctor?.duplicate_count || 0} issues</strong><small>{doctor?.repeated_artists || 0} repeated artists · {doctor?.energy_jumps || 0} jumps</small></div></div><div className="track-table playlist-table">{activePlaylist.tracks.map((t,i)=><TrackRow key={t.id} t={t} index={i+1} onPlay={onPlay} />)}</div></section>;
  return <section className="page-stack"><div className="section-head"><div><div className="eyebrow">YOUR COLLECTION</div><h2>Playlists, with intent.</h2><p>Build sets, flows and moods without tying a playlist to a downloaded file.</p></div><button className="primary-button" onClick={create}>＋ New playlist</button></div><div className="playlist-grid">{playlists.map((p,i)=><button key={p.id} className="playlist-card-new" onClick={() => openPlaylist(p)}><div className={`playlist-cover-small p${(i%6)+1}`} style={p.artwork_url ? {backgroundImage:`url(${p.artwork_url})`} : undefined}><span>♫</span></div><div className="playlist-card-meta"><strong>{p.name}</strong><span>{p.tracks.length} tracks</span><small>{p.description || "NOMAD playlist"}</small></div><b>→</b></button>)}</div>{!playlists.length&&<EmptyState icon="▣" title="Your first playlist starts here" text="Create a blank playlist now, then use NOMAD AI to shape it." />}</section>;
}

function AIView({vibe,setVibe,vibeResult,interpret,journey,radio}:{vibe:string;setVibe:(v:string)=>void;vibeResult:Record<string,unknown>|null;interpret:()=>void;journey:()=>void;radio:()=>void}) {
  return <section className="page-stack"><section className="ai-hero-new"><div className="ai-copy"><div className="eyebrow">NOMAD INTELLIGENCE</div><h2>Describe the moment.<br /><em>We’ll shape the music.</em></h2><p>The language layer interprets intent. The recommendation engine handles candidate selection, scoring and flow.</p><div className="ai-input"><textarea value={vibe} onChange={e=>setVibe(e.target.value)} placeholder="late-night coding · darker · more discovery · no acoustic…"/><div className="ai-input-foot"><span>Try: <b>“cinematic sunrise, 20% familiar, 80% discovery”</b></span><button className="primary-button" onClick={interpret}>Interpret vibe →</button></div></div></div><div className="ai-visual"><div className="ai-rings r1"/><div className="ai-rings r2"/><div className="ai-core">N</div><span className="ai-label a1">TASTE</span><span className="ai-label a2">VIBE</span><span className="ai-label a3">FLOW</span></div></section>{vibeResult&&<div className="ai-result"><div><div className="eyebrow">INTERPRETED VIBE</div><strong>Ready for the recommendation engine</strong></div><pre>{JSON.stringify(vibeResult,null,2)}</pre></div>}<div className="signature-tools"><Tool title="Vibe Match" copy="Find tracks that feel like this exact moment." onClick={interpret}/><Tool title="Smart Radio" copy="Keep the current mood moving." onClick={radio}/><Tool title="Vibe Journey" copy="Turn intent into a 45-minute arc." onClick={journey}/><Tool title="Playlist Doctor" copy="Fix flow, duplicates and artist repetition." onClick={()=>undefined}/></div></section>;
}
function Tool({title,copy,onClick}:{title:string;copy:string;onClick:()=>void}) { return <button className="tool-new" onClick={onClick}><div><strong>{title}</strong><span>{copy}</span></div><b>↗</b></button>; }

function TrackRow({t,onPlay,onLyrics,meta,index,compact=false}:{t?:Track;onPlay:(t:Track,append?:boolean)=>void;onLyrics?:()=>void;meta?:string;index?:number;compact?:boolean}) {
  if (!t) return null;
  const srcs = (t.sources || []).filter(s => s.available !== false).slice(0,3);
  return <div className={`track-row ${compact ? "compact" : ""}`}>
    <div className="row-index">{index ? String(index).padStart(2,"0") : "•"}</div>
    <div className="row-art" style={artStyle(t)}><button onClick={() => onPlay(t)}>▶</button></div>
    <div className="row-copy"><strong>{t.title}</strong><span>{t.artist_name || "Unknown artist"}{t.album_name ? ` · ${t.album_name}` : ""}</span></div>
    <div className="row-source">{srcs.map(s => <i key={`${s.provider}-${s.provider_id}`}>{s.provider}</i>)}</div>
    <div className="row-meta">{meta || (t.duration_ms ? fmtTime(t.duration_ms) : "")}</div>
    <div className="row-menu"><button onClick={onLyrics}>♪</button><button onClick={() => onPlay(t,true)}>＋</button></div>
  </div>;
}
function EmptyState({icon,title,text,compact=false}:{icon:string;title:string;text:string;compact?:boolean}) { return <div className={`empty-state ${compact ? "compact" : ""}`}><div className="empty-icon">{icon}</div><strong>{title}</strong><span>{text}</span></div>; }
function ConnectionsModal({providers,onClose,onConnect}:{providers:Provider[];onClose:()=>void;onConnect:(provider:string)=>void}) { return <div className="modal-backdrop" onMouseDown={onClose}><div className="modal-card connections" onMouseDown={e=>e.stopPropagation()}><div className="modal-head"><div><div className="eyebrow">SOURCE HUB</div><h3>Your music connections</h3><p>Connect a provider once. NOMAD keeps the graph unified.</p></div><button onClick={onClose}>×</button></div>{providers.filter(p => ["spotify","youtube","deezer","apple"].includes(p.name)).map(p=>{const state=p.connected||p.authenticated?"Connected":p.configured?(p.mode==="public_metadata"?"Ready":"Ready to connect"):"Needs setup"; return <div className="connect-row" key={p.name}><div className={`provider-logo ${p.name}`}>{p.name[0].toUpperCase()}</div><div><strong>{p.name}</strong><span>{p.account_name || p.mode}</span></div><div className="connect-status"><Dot state={state==="Connected"?"good":state==="Ready"?"ready":"muted"}/>{state}</div><button className="outline-button small" disabled={state==="Connected" || state==="Ready"&&p.mode==="public_metadata"} onClick={()=>onConnect(p.name)}>{state==="Connected"?"Connected":state==="Ready"?"Open":"Connect"}</button></div>})}<div className="modal-note">Spotify and YouTube require the credentials configured in your local .env. Deezer and Apple are metadata-only sources here.</div></div></div>; }
function CreatePlaylistModal({name,description,setName,setDescription,onCancel,onCreate}:{name:string;description:string;setName:(v:string)=>void;setDescription:(v:string)=>void;onCancel:()=>void;onCreate:()=>void}) { return <div className="modal-backdrop" onMouseDown={onCancel}><div className="modal-card" onMouseDown={e=>e.stopPropagation()}><div className="modal-head"><div><div className="eyebrow">NEW PLAYLIST</div><h3>Give it a reason to exist.</h3></div><button onClick={onCancel}>×</button></div><label>Playlist name<input autoFocus value={name} onChange={e=>setName(e.target.value)} placeholder="Midnight Drive"/></label><label>Description<textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Dark cinematic night journey…"/></label><div className="modal-actions"><button className="outline-button" onClick={onCancel}>Cancel</button><button className="primary-button" onClick={onCreate}>Create playlist</button></div></div></div>; }
function LyricsDrawer({track,lyrics,activeLyric,onClose,onSeek}:{track:Track|null;lyrics:{found:boolean;plain:string;synced:string;source?:string|null;offset_ms?:number;lines?:LyricLine[]};activeLyric:number;onClose:()=>void;onSeek:(ms:number)=>void}) { return <aside className="immersion-drawer"><div className="drawer-top"><div><div className="eyebrow">NOW PLAYING · LYRICS</div><h3>{track?.title || "Nothing playing"}</h3><span>{track?.artist_name || ""}</span></div><button onClick={onClose}>×</button></div>{lyrics.found && lyrics.lines?.length ? <div className="lyrics-flow">{lyrics.lines.map((line,i)=><button key={`${line.time_ms}-${i}`} className={i===activeLyric?"active":""} onClick={()=>onSeek(line.time_ms-(lyrics.offset_ms||0))}>{line.text || "♪"}</button>)}</div> : lyrics.found ? <pre className="lyrics-plain">{lyrics.plain || lyrics.synced}</pre> : <EmptyState icon="♪" title="Lyrics are being indexed" text="Try opening them again in a moment." compact />}</aside>; }
function QueueDrawer({queue,library,results,radio,journey,onClose,onPlay}:{queue:QueueState|null;library:Track[];results:Track[];radio:Track[];journey:Track[];onClose:()=>void;onPlay:(t:Track,append?:boolean)=>void}) { const pool=[...library,...results,...radio,...journey]; const lookup=new Map(pool.map(t=>[t.id,t])); return <aside className="immersion-drawer queue-drawer-new"><div className="drawer-top"><div><div className="eyebrow">QUEUE</div><h3>{queue?.items?.length || 0} tracks in flow</h3><span>{queue?.shuffle?"Smart shuffle":"Ordered"} · {queue?.repeat || "off"}</span></div><button onClick={onClose}>×</button></div><div className="queue-now"><span>NOW PLAYING</span><strong>{queue?.current_item_id ? lookup.get(queue.items.find(x=>x.id===queue.current_item_id)?.track_id || "")?.title || "Unknown" : "Nothing"}</strong></div><div className="queue-list">{queue?.items?.map(item=>{const t=lookup.get(item.track_id); return t?<TrackRow key={item.id} t={t} compact index={item.position+1} meta={item.id===queue.current_item_id?"NOW PLAYING":""} onPlay={onPlay}/>:null})}</div></aside>; }
