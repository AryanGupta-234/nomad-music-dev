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
        return true;
      } catch (e) {
        flash(e instanceof Error ? e.message : "Spotify playback unavailable");
        return false;
      }
    }
    if (resolved?.provider === "youtube" && resolved?.source) {
      const url = String(resolved.source).includes("http") ? String(resolved.source) : `https://www.youtube.com/watch?v=${resolved.source}`;
      window.open(url, "_blank", "noopener,noreferrer");
      flash("Opened YouTube playback source");
      return true;
    }
    return false;
  }

  async function interpretVibe() {
    setBusy(true);
    try {
      const d = await fetch(`${API}/vibe?q=${encodeURIComponent(vibe)}`).then(r => r.json());
      setVibeResult(d.query || d);
      flash("Vibe interpreted by NOMAD.");
    } catch (e) { flash(e instanceof Error ? e.message : "Vibe engine unavailable"); }
    finally { setBusy(false); }
  }

  async function startRadio(track?: Track) {
    setBusy(true);
    try {
      const d = await fetch(`${API}/radio?limit=18${track ? `&seed_track_id=${encodeURIComponent(track.id)}` : ""}`).then(r => r.json());
      setRadio(d.tracks || []);
      setActive("Discover");
      flash("Smart Radio generated a new flow.");
    } catch (e) { flash(e instanceof Error ? e.message : "Radio unavailable"); }
    finally { setBusy(false); }
  }

  async function startJourney() {
    setBusy(true);
    try {
      const d = await fetch(`${API}/vibe/journey?target_minutes=45&limit=24`).then(r => r.json());
      setJourney(d.tracks || []);
      setActive("Discover");
      flash("Vibe Journey is ready.");
    } catch (e) { flash(e instanceof Error ? e.message : "Vibe Journey unavailable"); }
    finally { setBusy(false); }
  }

  useEffect(() => { void refresh().catch(e => flash(e instanceof Error ? e.message : "Backend unavailable")); }, []);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); searchRef.current?.focus(); }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "l" && nowPlaying) { e.preventDefault(); void loadLyrics(nowPlaying.id, true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [nowPlaying]);

  const recTracks = recommendations.map(r => recMap.get(r.track_id)).filter(Boolean) as Track[];
  const content = () => {
    if (active === "Search") return <SearchPage results={results} query={query} busy={busy} onSync={syncSearch} onPlay={(t) => void resolveAndQueue(t)} onQueue={(t) => void resolveAndQueue(t, true)} onLyrics={(t) => void loadLyrics(t.id)} />;
    if (active === "Discover") return <DiscoverPage recommendations={recTracks} radio={radio} journey={journey} onPlay={(t) => void resolveAndQueue(t)} onRadio={() => void startRadio(nowPlaying || undefined)} onJourney={() => void startJourney()} />;
    if (active === "Library") return <LibraryPage tracks={library} localRoot={localRoot} busy={busy} onRoot={setLocalRoot} onIndex={indexLocalLibrary} onPlay={(t) => void resolveAndQueue(t)} onLyrics={(t) => void loadLyrics(t.id)} />;
    if (active === "Playlists") return <PlaylistsPage playlists={playlists} onCreate={() => setNewPlaylistOpen(true)} onOpen={setActivePlaylist} onPlay={(t) => void resolveAndQueue(t)} />;
    if (active === "AI / Vibe") return <VibePage vibe={vibe} setVibe={setVibe} result={vibeResult} busy={busy} onInterpret={interpretVibe} onRadio={() => void startRadio(nowPlaying || undefined)} onJourney={() => void startJourney()} />;
    return <HomePage library={library} recs={recTracks} nowPlaying={nowPlaying} providers={providers} onPlay={(t) => void resolveAndQueue(t)} onDiscover={() => setActive("Discover")} onLibrary={() => setActive("Library")} />;
  };

  return <div className="nomad-app">
    <aside className="sidebar">
      <div className="brand-block"><div className="brand-mark">N<i/></div><div><div className="brand-name">NOMAD</div><div className="brand-sub">MUSIC INTELLIGENCE</div></div></div>
      <div className="engine-chip"><span className="live-dot"/> Local Engine <b>ONLINE</b></div>
      <nav className="nav-section"><span>NAVIGATION</span>{NAV.map(n => <button key={n.id} className={`nav-item ${active === n.id ? "active" : ""}`} onClick={() => setActive(n.id)}><span className="nav-icon">{n.icon}</span>{n.label}{n.id === "AI / Vibe" && <em>AI</em>}</button>)}</nav>
      <div className="sidebar-spacer"/>
      <button className="connection-card" onClick={() => setShowConnections(true)}><div className="connection-title"><span>SOURCE HUB</span><span>→</span></div>{["spotify","youtube"].map(name => { const s = providerState(name); return <div className="connection-mini-row" key={name}><i className={`status-led ${s.tone}`}/><b>{name}</b><small>{s.label}</small></div> })}</button>
      <div className="sidebar-foot">NOMAD V3 · STABILIZATION BUILD</div>
    </aside>
    <main className="main-shell">
      <header className="topbar"><div className="page-heading"><div className="eyebrow">NOMAD MUSIC</div><h1>{active === "Home" ? "Good evening" : active}</h1><p>Unified local music, provider search, intelligence and playback.</p></div><div className={`global-search ${searchFocus ? "focus" : ""}`}><span>⌕</span><input ref={searchRef} value={query} onFocus={() => setSearchFocus(true)} onBlur={() => setSearchFocus(false)} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && void search()} placeholder="Search songs, artists, albums…"/><kbd>Ctrl K</kbd><button onClick={() => void search()}>{busy ? "…" : "Search"}</button></div></header>
      {toast && <div className="toast"><i className="toast-pulse"/>{toast}</div>}
      <div className="page-stack">{content()}</div>
    </main>
    <Player nowPlaying={nowPlaying} queue={queue} resolution={resolution} position={position} duration={duration} liked={liked} expanded={isExpandedPlayer} onExpand={() => setIsExpandedPlayer(v => !v)} onToggle={togglePlayback} onNext={() => void control("next")} onPrevious={() => void control("previous")} onSeek={seekLocal} onVolume={setVolume} onLyrics={() => nowPlaying && void loadLyrics(nowPlaying.id, true)} onQueue={() => setShowQueue(true)} onLike={() => nowPlaying && void favorite(nowPlaying)} />
    {showQueue && <QueueDrawer queue={queue} tracks={new Map(library.concat(results, radio, journey).map(t => [t.id, t]))} onClose={() => setShowQueue(false)} onPlay={(t) => void resolveAndQueue(t)} />}
    {showLyrics && <LyricsDrawer track={nowPlaying} lyrics={lyrics} active={activeLyric} onClose={() => setShowLyrics(false)} onSeek={seekLocal} />}
    {showConnections && <Connections providers={providers} onClose={() => setShowConnections(false)} onConnect={connect} />}
    {newPlaylistOpen && <NewPlaylistModal name={newPlaylistName} description={newPlaylistDescription} setName={setNewPlaylistName} setDescription={setNewPlaylistDescription} onClose={() => setNewPlaylistOpen(false)} onCreate={async () => { if (!newPlaylistName.trim()) return; try { const r = await fetch(`${API}/playlists`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newPlaylistName.trim(), description: newPlaylistDescription.trim() || null }) }); if (!r.ok) throw new Error(await r.text()); await refresh(); setNewPlaylistName(""); setNewPlaylistDescription(""); setNewPlaylistOpen(false); flash("Playlist created."); } catch (e) { flash(e instanceof Error ? e.message : "Could not create playlist"); } }} />}
    {activePlaylist && <PlaylistModal playlist={activePlaylist} onClose={() => setActivePlaylist(null)} onPlay={(t) => void resolveAndQueue(t)} />}
  </div>;
}

function HomePage({library,recs,nowPlaying,providers,onPlay,onDiscover,onLibrary}:{library:Track[];recs:Track[];nowPlaying:Track|null;providers:Provider[];onPlay:(t:Track)=>void;onDiscover:()=>void;onLibrary:()=>void}){const recent=library.slice(0,5);return <><section className="home-hero-new"><div className="hero-copy-new"><div className="eyebrow">PERSONAL MUSIC INTELLIGENCE</div><h2>Music that feels <em>specifically yours.</em></h2><p>Discover, organize and play your music across local files and connected providers from one calm workspace.</p><div className="hero-actions"><button className="primary-button" onClick={onDiscover}>Explore for you</button><button className="outline-button" onClick={onLibrary}>Open library</button></div><div className="hero-trust"><span><i className="live-dot"/> {providers.filter(p=>p.configured).length} configured sources</span><span>Queue state synced</span>{nowPlaying&&<button onClick={()=>onPlay(nowPlaying)}>▶ Resume {nowPlaying.title}</button>}</div></div><div className="hero-art-stage"><div className="hero-orbit one"/><div className="hero-orbit two"/><div className="hero-art-stack">{recent.slice(0,3).map((t,i)=><div key={t.id} className={`hero-art-card c${i+1}`} style={artStyle(t)}/>)}</div><div className="hero-core">N</div>{nowPlaying&&<div className="hero-caption"><span>NOW PLAYING</span><strong>{nowPlaying.title}</strong></div>}</div></section><div className="rail-head"><div><div className="eyebrow">CONTINUE LISTENING</div><h3>{nowPlaying?.title || "Your library"}</h3></div><button onClick={onLibrary}>View library →</button></div><div className="cover-rail">{recent.map(t=><MusicCard key={t.id} track={t} onPlay={onPlay}/>)}</div><div className="rail-head"><div><div className="eyebrow">MADE FOR YOU</div><h3>Recommendations</h3></div><button onClick={onDiscover}>Open Discover →</button></div><div className="cover-rail">{recs.length?recs.map(t=><MusicCard key={t.id} track={t} onPlay={onPlay}/>):recent.map(t=><MusicCard key={`fallback-${t.id}`} track={t} onPlay={onPlay}/>)}</div></>}
function MusicCard({track,onPlay}:{track:Track;onPlay:(t:Track)=>void}){return <button className="music-card" onClick={()=>onPlay(track)}><div className="music-card-art" style={artStyle(track)}><span className="card-play">▶</span></div><strong>{track.title}</strong><span>{artistOf(track)}</span><small>{track.album_name || "TRACK"}</small></button>}
function SearchPage({results,query,busy,onSync,onPlay,onQueue,onLyrics}:{results:Track[];query:string;busy:boolean;onSync:()=>void;onPlay:(t:Track)=>void;onQueue:(t:Track)=>void;onLyrics:(t:Track)=>void}){return <><div className="section-head"><div><div className="eyebrow">UNIFIED SEARCH</div><h2>{query ? `Results for “${query}”` : "Search"}</h2><p>Local and provider results are normalized into the same NOMAD track model.</p></div><button className="outline-button" onClick={onSync} disabled={busy}>{busy?"Refreshing…":"Sync provider results"}</button></div>{results.length?<div className="track-table">{results.map((t,i)=><TrackRow key={t.id} i={i} track={t} onPlay={onPlay} onQueue={onQueue} onLyrics={onLyrics}/>)}</div>:<EmptyState title="Nothing here yet" text="Search for a song, artist or album to populate the unified result view."/>}</>}
function DiscoverPage({recommendations,radio,journey,onPlay,onRadio,onJourney}:{recommendations:Track[];radio:Track[];journey:Track[];onPlay:(t:Track)=>void;onRadio:()=>void;onJourney:()=>void}){const all=radio.length?radio:recommendations;return <><div className="section-head"><div><div className="eyebrow">DISCOVERY ENGINE</div><h2>Follow the feeling.</h2><p>Smart Radio and Vibe Journey are layered on top of your actual library and provider graph.</p></div><div className="hero-actions"><button className="primary-button" onClick={onRadio}>Start Smart Radio</button><button className="outline-button" onClick={onJourney}>Build Vibe Journey</button></div></div><div className="home-grid"><div className="surface large"><div className="surface-head"><div><div className="eyebrow">RECOMMENDED</div><h3>{radio.length?"Smart Radio":"Made For You"}</h3></div></div><div className="mini-list">{all.length?all.slice(0,6).map((t,i)=><TrackRow key={t.id} i={i} track={t} onPlay={onPlay} onQueue={onPlay} onLyrics={()=>{}} compact/>):<EmptyState title="Start discovery" text="Generate Smart Radio or open Vibe Journey."/>}</div></div><div className="surface"><div className="eyebrow">VIBE JOURNEY</div><h3 style={{fontSize:22,margin:"7px 0"}}>Energy with an arc.</h3><p style={{fontSize:10,color:"#727b89",lineHeight:1.6}}>Chill → groove → energy → peak → cooldown, rather than a random playlist shuffle.</p><button className="primary-button" onClick={onJourney}>Generate 45-minute journey</button></div></div>{journey.length>0&&<><div className="rail-head"><div><div className="eyebrow">CURRENT JOURNEY</div><h3>{journey.length} tracks sequenced</h3></div></div><div className="cover-rail">{journey.slice(0,5).map(t=><MusicCard key={t.id} track={t} onPlay={onPlay}/>)}</div></>}</>}
function LibraryPage({tracks,localRoot,busy,onRoot,onIndex,onPlay,onLyrics}:{tracks:Track[];localRoot:string;busy:boolean;onRoot:(v:string)=>void;onIndex:()=>void;onPlay:(t:Track)=>void;onLyrics:(t:Track)=>void}){return <><div className="section-head"><div><div className="eyebrow">CANONICAL MUSIC GRAPH</div><h2>Your Library</h2><p>Local-first music with provider metadata normalized into one collection.</p></div></div><div className="surface"><div style={{display:"flex",gap:9}}><input value={localRoot} onChange={e=>onRoot(e.target.value)} placeholder="C:\\Music" style={{flex:1,border:"1px solid rgba(255,255,255,.08)",background:"#0c1015",color:"#f4f6f7",borderRadius:10,padding:"10px",fontSize:10}}/><button className="primary-button" onClick={onIndex} disabled={busy}>{busy?"Indexing…":"Index folder"}</button></div></div><div className="track-table">{tracks.length?tracks.map((t,i)=><TrackRow key={t.id} i={i} track={t} onPlay={onPlay} onQueue={onPlay} onLyrics={onLyrics}/>):<EmptyState title="Library is empty" text="Index your Music folder to start building the NOMAD graph."/>}</div></>}
function PlaylistsPage({playlists,onCreate,onOpen,onPlay}:{playlists:Playlist[];onCreate:()=>void;onOpen:(p:Playlist)=>void;onPlay:(t:Track)=>void}){return <><div className="section-head"><div><div className="eyebrow">YOUR COLLECTION</div><h2>Playlists</h2><p>Create sets, inspect their tracks and keep playback state unified.</p></div><button className="primary-button" onClick={onCreate}>＋ New playlist</button></div>{playlists.length?<div className="discover-strip">{playlists.map(p=><button key={p.id} className="discover-tile" onClick={()=>onOpen(p)}><div style={p.artwork_url?{backgroundImage:`url(${p.artwork_url})`}:undefined}/><span>PLAYLIST · {p.tracks.length} TRACKS</span><strong>{p.name}</strong></button>)}</div>:<EmptyState title="No playlists yet" text="Create your first playlist from the collection."/>}</>}
function VibePage({vibe,setVibe,result,busy,onInterpret,onRadio,onJourney}:{vibe:string;setVibe:(v:string)=>void;result:Record<string,unknown>|null;busy:boolean;onInterpret:()=>void;onRadio:()=>void;onJourney:()=>void}){return <><div className="section-head"><div><div className="eyebrow">NOMAD INTELLIGENCE</div><h2>Describe the moment.</h2><p>Use natural language, then turn the interpreted vibe into a radio flow or a longer journey.</p></div></div><div className="surface"><textarea value={vibe} onChange={e=>setVibe(e.target.value)} rows={5} style={{width:"100%",resize:"vertical",border:"1px solid rgba(255,255,255,.08)",background:"#0c1015",color:"#f4f6f7",outline:0,borderRadius:10,padding:12,fontSize:11}}/><div className="hero-actions" style={{marginTop:10}}><button className="primary-button" onClick={onInterpret} disabled={busy}>{busy?"Interpreting…":"Interpret vibe"}</button><button className="outline-button" onClick={onRadio}>Smart Radio</button><button className="outline-button" onClick={onJourney}>Vibe Journey</button></div>{result&&<pre style={{whiteSpace:"pre-wrap",marginTop:15,color:"#9bd8ba",background:"#080b0f",padding:12,borderRadius:10,fontSize:9}}>{JSON.stringify(result,null,2)}</pre>}</div></>}
function TrackRow({i,track,onPlay,onQueue,onLyrics,compact=false}:{i:number;track:Track;onPlay:(t:Track)=>void;onQueue:(t:Track)=>void;onLyrics:(t:Track)=>void;compact?:boolean}){return <div className={`track-row ${compact?"compact":""}`}><span className="row-index">{String(i+1).padStart(2,"0")}</span><div className="row-art" style={artStyle(track)}><button aria-label={`Play ${track.title}`} onClick={()=>onPlay(track)}>▶</button></div><div style={{minWidth:0}}><b style={{display:"block",fontSize:10,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{track.title}</b><span style={{display:"block",fontSize:9,color:"#737c88",marginTop:3}}>{artistOf(track)}{track.album_name?` · ${track.album_name}`:""}</span></div><span style={{fontSize:8,color:"#626b76"}}>{(track.sources||[]).map(s=>s.provider).join(" · ")}</span><span style={{fontSize:8,color:"#626b76"}}>{track.duration_ms?fmtTime(track.duration_ms):""}</span><div style={{display:"flex",justifyContent:"flex-end",gap:4}}><button className="ghost-button" onClick={()=>onLyrics(track)}>Lyrics</button><button className="ghost-button" onClick={()=>onQueue(track)}>＋</button></div></div>}
function EmptyState({title,text}:{title:string;text:string}){return <div className="surface" style={{textAlign:"center",padding:"50px 20px"}}><div style={{fontSize:28,color:"#58616d"}}>◌</div><h3 style={{fontSize:15,margin:"8px 0"}}>{title}</h3><p style={{fontSize:10,color:"#727b89",margin:0}}>{text}</p></div>}
function Player({nowPlaying,queue,resolution,position,duration,liked,expanded,onExpand,onToggle,onNext,onPrevious,onSeek,onVolume,onLyrics,onQueue,onLike}:{nowPlaying:Track|null;queue:QueueState|null;resolution:any;position:number;duration:number;liked:boolean;expanded:boolean;onExpand:()=>void;onToggle:()=>void;onNext:()=>void;onPrevious:()=>void;onSeek:(v:number)=>void;onVolume:(v:number)=>void;onLyrics:()=>void;onQueue:()=>void;onLike:()=>void}){return <footer className={`bottom-player ${expanded?"expanded":""}`}><div className="player-art" style={artStyle(nowPlaying)}/><div className="player-meta"><b>{nowPlaying?.title||"Nothing playing"}</b><span>{artistOf(nowPlaying)}{resolution?.provider?` · ${resolution.provider}`:""}</span></div><button className="ghost-button" onClick={onPrevious}>◀</button><button className="primary-button" onClick={onToggle}>{queue?.is_playing?"Ⅱ":"▶"}</button><button className="ghost-button" onClick={onNext}>▶</button><div style={{flex:1,minWidth:120,display:"flex",alignItems:"center",gap:7}}><input type="range" min={0} max={Math.max(duration,nowPlaying?.duration_ms||1)} value={Math.min(position,Math.max(duration,nowPlaying?.duration_ms||1))} onChange={e=>onSeek(Number(e.target.value))} style={{width:"100%"}}/><span style={{fontSize:7,color:"#69717d",whiteSpace:"nowrap"}}>{fmtTime(position)} / {fmtTime(duration||nowPlaying?.duration_ms||0)}</span></div><button className="ghost-button" onClick={onLike}>{liked?"♥":"♡"}</button><button className="ghost-button" onClick={onLyrics}>♪</button><input type="range" min="0" max="1" step=".01" defaultValue={queue?.volume??.8} onChange={e=>onVolume(Number(e.target.value))} style={{width:75}}/><button className="ghost-button" onClick={onQueue}>☰</button><button className="ghost-button" onClick={onExpand}>{expanded?"×":"↗"}</button></footer>}
function QueueDrawer({queue,tracks,onClose,onPlay}:{queue:QueueState|null;tracks:Map<string,Track>;onClose:()=>void;onPlay:(t:Track)=>void}){return <aside className="drawer queue-drawer" style={{position:"fixed",right:0,top:0,bottom:78,width:"min(420px,42vw)",zIndex:90,background:"rgba(10,14,18,.98)",borderLeft:"1px solid rgba(255,255,255,.08)",padding:18,overflow:"auto"}}><div className="rail-head"><div><div className="eyebrow">QUEUE</div><h3>{queue?.items.length||0} tracks</h3></div><button onClick={onClose}>×</button></div>{queue?.items.map((i,n)=>{const t=tracks.get(i.track_id);return t?<button key={i.id} className="track-row compact" style={{width:"100%",border:0,textAlign:"left"}} onClick={()=>onPlay(t)}><span className="row-index">{String(n+1).padStart(2,"0")}</span><div className="row-art" style={artStyle(t)}/><div><b style={{fontSize:9}}>{t.title}</b><span style={{display:"block",fontSize:8,color:"#717a86"}}>{artistOf(t)}</span></div><span/><span/><span/></button>:null})}</aside>}
function LyricsDrawer({track,lyrics,active,onClose,onSeek}:{track:Track|null;lyrics:{found:boolean;plain:string;synced:string;lines?:LyricLine[];source?:string|null};active:number;onClose:()=>void;onSeek:(v:number)=>void}){return <aside className="drawer lyrics-drawer" style={{position:"fixed",right:0,top:0,bottom:78,width:"min(520px,48vw)",zIndex:91,background:"rgba(10,14,18,.98)",borderLeft:"1px solid rgba(255,255,255,.08)",padding:24,overflow:"auto"}}><div className="rail-head"><div><div className="eyebrow">LYRICS</div><h3>{track?.title||"Nothing playing"}</h3></div><button onClick={onClose}>×</button></div><p style={{fontSize:9,color:"#727b89"}}>{artistOf(track)} · {lyrics.source||"cached / provider"}</p>{lyrics.lines?.length?<div style={{marginTop:22}}>{lyrics.lines.map((l,i)=><button key={`${l.time_ms}-${i}`} className="ghost-button" style={{display:"block",width:"100%",textAlign:"left",fontSize:i===active?18:14,color:i===active?"#f4f7f5":"#66707d",padding:"7px 0"}} onClick={()=>onSeek(l.time_ms)}>{l.text||"♪"}</button>)}</div>:lyrics.plain?<pre style={{whiteSpace:"pre-wrap",fontSize:12,lineHeight:1.7,color:"#cbd2d4"}}>{lyrics.plain}</pre>:<EmptyState title="No lyrics found" text="NOMAD will show synchronized lyrics when a source returns them."/>}</aside>}
function Connections({providers,onClose,onConnect}:{providers:Provider[];onClose:()=>void;onConnect:(p:string)=>void}){return <div className="modal" style={{position:"fixed",inset:0,zIndex:100,background:"rgba(0,0,0,.68)",display:"grid",placeItems:"center"}}><div className="dialog" style={{width:460}}><button className="close" onClick={onClose}>×</button><div className="eyebrow">SOURCE HUB</div><h3>Connections</h3>{providers.filter(p=>["spotify","youtube"].includes(p.name)).map(p=><div key={p.name} style={{display:"flex",justifyContent:"space-between",padding:"14px 0",borderTop:"1px solid rgba(255,255,255,.07)"}}><div><b style={{textTransform:"capitalize"}}>{p.name}</b><span style={{display:"block",fontSize:8,color:"#737c88",marginTop:4}}>{providerStateFor(p)}</span></div><button className="outline-button" disabled={!!p.connected} onClick={()=>onConnect(p.name)}>{p.connected?"Connected":"Connect"}</button></div>)}</div></div>}
function providerStateFor(p:Provider){if(p.connected||p.authenticated)return p.account_name?`Connected · ${p.account_name}`:"Connected";if(p.configured)return p.mode==="public_metadata"?"Ready":"Ready to connect";return "Not configured"}
function NewPlaylistModal({name,description,setName,setDescription,onClose,onCreate}:{name:string;description:string;setName:(v:string)=>void;setDescription:(v:string)=>void;onClose:()=>void;onCreate:()=>void}){return <div className="modal" style={{position:"fixed",inset:0,zIndex:100,background:"rgba(0,0,0,.68)",display:"grid",placeItems:"center"}}><div className="dialog"><button className="close" onClick={onClose}>×</button><div className="eyebrow">PLAYLIST</div><h3>New playlist</h3><input value={name} onChange={e=>setName(e.target.value)} placeholder="Midnight Drive" style={{width:"100%",marginBottom:9}}/><textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe the set" rows={4} style={{width:"100%",background:"#0c1015",color:"#f4f6f7",border:"1px solid rgba(255,255,255,.08)",borderRadius:9,padding:10}}/><div className="hero-actions" style={{justifyContent:"flex-end",marginTop:10}}><button className="outline-button" onClick={onClose}>Cancel</button><button className="primary-button" onClick={onCreate}>Create</button></div></div></div>}
function PlaylistModal({playlist,onClose,onPlay}:{playlist:Playlist;onClose:()=>void;onPlay:(t:Track)=>void}){return <div className="modal" style={{position:"fixed",inset:0,zIndex:100,background:"rgba(0,0,0,.68)",display:"grid",placeItems:"center"}}><div className="dialog" style={{width:"min(760px,92vw)",maxHeight:"86vh",overflow:"auto"}}><button className="close" onClick={onClose}>×</button><div className="eyebrow">PLAYLIST · {playlist.tracks.length} TRACKS</div><h3>{playlist.name}</h3><p style={{fontSize:10,color:"#727b89"}}>{playlist.description||""}</p>{playlist.tracks.map((t,i)=><TrackRow key={t.id} i={i} track={t} onPlay={onPlay} onQueue={onPlay} onLyrics={()=>{}} compact/>)}</div></div>}
