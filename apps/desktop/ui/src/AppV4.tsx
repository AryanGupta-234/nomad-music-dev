import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import "./AppV4.css";

type Source = { provider: string; provider_id?: string; playback_kind?: string | null; uri?: string | null; available?: boolean };
type Track = { id: string; title: string; artist_name?: string | null; album_name?: string | null; duration_ms?: number | null; artwork_url?: string | null; artist_id?: string | null; sources?: Source[] };
type Playlist = { id: string; name: string; description?: string | null; artwork_url?: string | null; tracks: Track[] };
type Queue = { current_item_id: string | null; is_playing: boolean; position_ms: number; volume: number; shuffle: boolean; repeat: string; items: { id: string; track_id: string; position: number }[] };
type Provider = { name: string; configured: boolean; connected?: boolean; authenticated?: boolean; mode: string; account_name?: string | null };
type Lyric = { time_ms: number; text: string };

const API = import.meta.env.VITE_NOMAD_API || "http://127.0.0.1:8765/api/v1";
const NAV = [
  ["Home", "Home"], ["Search", "Search"], ["Discover", "Discover"],
  ["Library", "Library"], ["Playlists", "Playlists"], ["AI / Vibe", "NOMAD AI"],
] as const;
const fmt = (ms = 0) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const p: Record<string, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/><path d="M9 20v-6h6v6"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    spark: <><path d="m12 3-1.4 5.6L5 10l5.6 1.4L12 17l1.4-5.6L19 10l-5.6-1.4Z"/><path d="m19 16-.7 2.3L16 19l2.3.7L19 22l.7-2.3L22 19l-2.3-.7Z"/></>,
    library: <><rect x="4" y="3" width="4" height="18" rx="1"/><rect x="10" y="3" width="4" height="18" rx="1"/><rect x="16" y="3" width="4" height="18" rx="1"/></>,
    playlist: <><path d="M4 6h11M4 11h11M4 16h7"/><path d="M17 14v6a2 2 0 1 0 2-2v-7h3"/></>,
    bot: <><rect x="4" y="7" width="16" height="13" rx="3"/><path d="M12 3v4M8 12h.01M16 12h.01M8 16c2 1.5 6 1.5 8 0"/></>,
    play: <path d="m8 5 11 7-11 7Z" fill="currentColor" stroke="none"/>,
    pause: <><path d="M8 5v14M16 5v14"/></>,
    next: <><path d="m5 4 10 8-10 8Z" fill="currentColor" stroke="none"/><path d="M19 4v16"/></>,
    prev: <><path d="m19 4-10 8 10 8Z" fill="currentColor" stroke="none"/><path d="M5 4v16"/></>,
    heart: <path d="M20.8 8.8c0 5.4-8.8 10.2-8.8 10.2S3.2 14.2 3.2 8.8A4.8 4.8 0 0 1 12 6.1a4.8 4.8 0 0 1 8.8 2.7Z"/>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    more: <><circle cx="5" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none"/></>,
    queue: <><path d="M4 6h13M4 11h13M4 16h8"/><path d="M17 15v5l4-2.5Z"/></>,
    shuffle: <><path d="M16 3h5v5M4 5h2c4 0 5 10 9 10h6M16 21h5v-5"/><path d="M4 19h2c1.5 0 2.5-1 3.3-2"/></>,
    repeat: <><path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/></>,
    lyrics: <><path d="M9 18V5l10-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.8 1.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-2.6V20a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1-1.8-1.8.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H6v-2.6h.4a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L9.4 6l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6v-.2H15v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3L18 6l1.8 1.8-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v2.6H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{p[name] || p.more}</svg>;
}

function TrackCard({ t, play, like, add }: { t: Track; play: (t: Track) => void; like?: (t: Track) => void; add?: (t: Track) => void }) {
  return <article className="track-card">
    <button className="cover-wrap" onClick={() => play(t)} aria-label={`Play ${t.title}`}>
      <img className="cover" src={t.artwork_url || ""} alt="" loading="lazy" />
      <span className="cover-play"><Icon name="play" /></span>
    </button>
    <div className="track-meta"><b title={t.title}>{t.title}</b><span title={t.artist_name || ""}>{t.artist_name || "Unknown artist"}</span></div>
    <div className="track-actions"><button onClick={() => like?.(t)} aria-label="Like"><Icon name="heart" /></button><button onClick={() => add?.(t)} aria-label="Add"><Icon name="plus" /></button><button aria-label="More"><Icon name="more" /></button></div>
  </article>;
}

function Rail({ title, subtitle, tracks, play, like, add, action }: { title: string; subtitle?: string; tracks: Track[]; play: (t: Track) => void; like?: (t: Track) => void; add?: (t: Track) => void; action?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const scroll = (n: number) => ref.current?.scrollBy({ left: n, behavior: "smooth" });
  if (!tracks.length) return null;
  return <section className="rail-section"><div className="section-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><div className="rail-controls"><button onClick={() => scroll(-720)}><Icon name="prev" size={15} /></button><button onClick={() => scroll(720)}><Icon name="next" size={15} /></button>{action && <button className="text-action">{action}<Icon name="arrow" size={14}/></button>}</div></div><div className="rail" ref={ref}>{tracks.map(t => <TrackCard key={t.id} t={t} play={play} like={like} add={add}/>)}</div></section>;
}

function TrackRows({ tracks, play, like, add }: { tracks: Track[]; play: (t: Track) => void; like?: (t: Track) => void; add?: (t: Track) => void }) {
  return <div className="rows">{tracks.map((t, i) => <div className="track-row" key={t.id}>
    <span className="row-num">{String(i + 1).padStart(2, "0")}</span><button className="row-art" onClick={() => play(t)}><img src={t.artwork_url || ""} alt="" /></button>
    <div className="row-title"><b>{t.title}</b><span>{t.artist_name || "Unknown artist"}</span></div><span className="row-album">{t.album_name || "—"}</span><span className="row-duration">{fmt(t.duration_ms || 0)}</span>
    <div className="row-actions"><button onClick={() => like?.(t)}><Icon name="heart"/></button><button onClick={() => add?.(t)}><Icon name="plus"/></button><button><Icon name="more"/></button></div>
  </div>)}</div>;
}

function Stat({ label, value }: { label: string; value: string | number }) { return <div className="stat"><b>{value}</b><span>{label}</span></div>; }

export default function AppV4() {
  const [view, setView] = useState("Home");
  const [query, setQuery] = useState("");
  const [library, setLibrary] = useState<Track[]>([]);
  const [results, setResults] = useState<Track[]>([]);
  const [recs, setRecs] = useState<Track[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [current, setCurrent] = useState<Track | null>(null);
  const [resolved, setResolved] = useState<any>(null);
  const [lyrics, setLyrics] = useState<Lyric[]>([]);
  const [activeLyric, setActiveLyric] = useState(-1);
  const [showLyrics, setShowLyrics] = useState(false);
  const [showQueue, setShowQueue] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [vibe, setVibe] = useState("dark cinematic night drive, more discovery");
  const [vibeResult, setVibeResult] = useState<any>(null);
  const [journey, setJourney] = useState<Track[]>([]);
  const [radio, setRadio] = useState<Track[]>([]);
  const [localRoot, setLocalRoot] = useState("");
  const [newPlaylist, setNewPlaylist] = useState("");
  const audio = useRef<HTMLAudioElement | null>(null);
  const toastTimer = useRef<number>();

  const all = useMemo(() => new Map([...library, ...results, ...recs, ...journey, ...radio, ...playlists.flatMap(p => p.tracks)].map(t => [t.id, t])), [library, results, recs, journey, radio, playlists]);
  const artistCount = new Set(library.map(t => t.artist_name).filter(Boolean)).size;

  const flash = (s: string) => { setToast(s); window.clearTimeout(toastTimer.current); toastTimer.current = window.setTimeout(() => setToast(""), 2600); };
  const get = async (path: string) => { const r = await fetch(`${API}${path}`); if (!r.ok) throw new Error(await r.text()); return r.json(); };
  const send = async (path: string, init: RequestInit) => { const r = await fetch(`${API}${path}`, init); if (!r.ok) throw new Error(await r.text()); return r.json(); };

  async function refresh() {
    try {
      const [lib, pls, rec, health, q] = await Promise.all([get("/library?limit=150"), get("/playlists"), get("/recommendations?limit=18"), get("/health/providers"), get("/player/queue").catch(() => null)]);
      setLibrary(lib.tracks || []); setPlaylists(Array.isArray(pls) ? pls : []); setRecs((rec.results || []).map((x: any) => x.track || x).filter(Boolean)); setProviders(health.providers || []); setQueue(q);
    } catch { flash("NOMAD backend is unavailable. UI remains usable with cached state."); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => () => window.clearTimeout(toastTimer.current), []);

  async function search() { if (!query.trim()) return; setBusy(true); try { const d = await get(`/search?q=${encodeURIComponent(query)}&limit=40`); setResults((d.results || []).map((x: any) => x.track || x).filter(Boolean)); setView("Search"); } catch (e) { flash(e instanceof Error ? e.message : "Search failed"); } finally { setBusy(false); } }
  async function play(t: Track, append = false) {
    setBusy(true);
    try {
      const ids = append ? [...(queue?.items || []).map(x => x.track_id), t.id] : [t.id];
      const q = await send(`/player/queue?start_index=${Math.max(0, ids.length - 1)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify([...new Set(ids)]) }); setQueue(q);
      const r = await get(`/tracks/${t.id}/resolve`); setResolved(r); setCurrent(t);
      await loadLyrics(t, false);
      if (r?.provider === "local") await playLocal(t); else flash(r?.provider ? `${r.provider} source resolved — connect that provider for playback.` : "No playable source resolved yet.");
    } catch (e) { flash(e instanceof Error ? e.message : "Playback failed"); } finally { setBusy(false); }
  }
  async function playLocal(t: Track) {
    const a = audio.current || new Audio(); audio.current = a; a.src = `${API}/tracks/${t.id}/audio`; a.preload = "auto"; a.volume = queue?.volume ?? .8;
    a.ontimeupdate = () => { const ms = a.currentTime * 1000; setPosition(ms); const ls = lyrics; let lo = 0, hi = ls.length - 1, best = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (ls[m].time_ms <= ms) { best = m; lo = m + 1; } else hi = m - 1; } setActiveLyric(best); };
    a.onloadedmetadata = () => setDuration(a.duration * 1000); a.onended = () => void move("next"); await a.play(); await send("/player/state?is_playing=true", { method: "PATCH" }).then(setQueue).catch(() => {});
  }
  async function move(dir: "next" | "previous") { try { const q = await send(`/player/${dir}`, { method: "POST" }); setQueue(q); const id = q?.current_item_id ? q.items.find((x: any) => x.id === q.current_item_id)?.track_id : null; const t = id ? all.get(id) : null; if (t) await play(t); } catch (e) { flash(e instanceof Error ? e.message : `${dir} failed`); } }
  async function toggle() { if (audio.current && resolved?.provider === "local") { if (audio.current.paused) await audio.current.play(); else audio.current.pause(); const q = await send(`/player/state?is_playing=${!audio.current.paused}&position_ms=${Math.round(audio.current.currentTime * 1000)}`, { method: "PATCH" }); setQueue(q); } else if (queue) setQueue(await send(`/player/state?is_playing=${!queue.is_playing}`, { method: "PATCH" })); }
  async function seek(v: number) { if (!audio.current) return; audio.current.currentTime = v / 1000; setPosition(v); void send(`/player/state?position_ms=${Math.round(v)}`, { method: "PATCH" }).catch(() => {}); }
  async function volume(v: number) { if (audio.current) audio.current.volume = v; try { setQueue(await send(`/player/state?volume=${v}`, { method: "PATCH" })); } catch {} }
  async function setMode(kind: "shuffle" | "repeat") { if (!queue) return; const v = kind === "shuffle" ? !queue.shuffle : queue.repeat === "off" ? "all" : queue.repeat === "all" ? "one" : "off"; try { setQueue(await send(`/player/state?${kind}=${v}`, { method: "PATCH" })); } catch {} }
  async function loadLyrics(t: Track, open = true) { try { const d = await get(`/tracks/${t.id}/lyrics`); setLyrics(d.lines || []); setActiveLyric(-1); if (open) setShowLyrics(true); } catch { setLyrics([]); if (open) setShowLyrics(true); } }
  async function like(t: Track) { try { await send(`/tracks/${t.id}/favorite?liked=true`, { method: "POST" }); flash("Added to Liked Songs"); } catch { flash("Could not update Likes"); } }
  const add = (t: Track) => flash(`Added ${t.title} to the next queue slot`);
  async function buildRadio() { try { const d = await get(`/radio?limit=18${current ? `&seed_track_id=${current.id}` : ""}`); setRadio((d.tracks || []).map((x: any) => all.get(x.id) || x).filter(Boolean)); setView("Discover"); } catch { flash("Smart Radio unavailable"); } }
  async function buildJourney() { try { const d = await get("/vibe/journey?target_minutes=45&limit=24"); setJourney((d.tracks || []).map((x: any) => all.get(x.id) || x).filter(Boolean)); setView("Discover"); } catch { flash("Vibe Journey unavailable"); } }
  async function interpretVibe() { try { setVibeResult(await get(`/vibe?q=${encodeURIComponent(vibe)}`)); } catch { flash("Vibe engine unavailable"); } }
  async function indexLocal() { if (!localRoot.trim()) return flash("Enter your music folder first"); setBusy(true); try { const d = await send(`/library/index?root=${encodeURIComponent(localRoot)}&recursive=true&limit=2000`, { method: "POST" }); await refresh(); flash(`Indexed ${d.indexed || 0} tracks`); } catch (e) { flash(e instanceof Error ? e.message : "Indexing failed"); } finally { setBusy(false); } }
  async function createPlaylist() { if (!newPlaylist.trim()) return; try { await send("/playlists", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newPlaylist, description: "Created in NOMAD" }) }); setNewPlaylist(""); await refresh(); flash("Playlist created"); } catch { flash("Could not create playlist"); } }

  const home = <>
    <section className="hero"><div className="hero-copy"><span className="eyebrow">NOMAD MUSIC INTELLIGENCE</span><h2>Your music.<br/><em>Your world.</em></h2><p>One library, one player, one intelligence layer across your local files and connected music sources.</p><div className="hero-actions"><button className="primary" onClick={() => current ? play(current) : library[0] && play(library[0])}><Icon name="play"/> {current ? "Resume listening" : "Start listening"}</button><button className="ghost" onClick={buildRadio}><Icon name="spark"/> Start Radio</button></div></div><div className="hero-art">{current?.artwork_url ? <img src={current.artwork_url} alt=""/> : <div className="hero-orb"><Icon name="spark" size={46}/></div>}<div className="hero-art-glow"/></div></section>
    <div className="stats-row"><Stat label="Tracks" value={library.length}/><Stat label="Artists" value={artistCount}/><Stat label="Playlists" value={playlists.length}/><Stat label="Sources" value={new Set(library.flatMap(t => (t.sources || []).map(s => s.provider))).size}/></div>
    <Rail title="Made For You" subtitle="Ranked from your actual listening graph" tracks={recs} play={play} like={like} add={add} action="See all"/>
    <Rail title="Continue Listening" subtitle="Pick up where you left off" tracks={library.slice(0, 12)} play={play} like={like} add={add}/>
    <section className="vibe-strip"><div><span className="eyebrow">YOUR VIBE</span><h3>Describe the moment. NOMAD builds the flow.</h3><p>Try “dark rainy coding”, “sunny indie morning”, or “aggressive gym set”.</p></div><div className="vibe-input"><input value={vibe} onChange={e => setVibe(e.target.value)} onKeyDown={e => e.key === "Enter" && interpretVibe()}/><button onClick={interpretVibe}><Icon name="arrow"/></button></div></section>
    <Rail title="New For You" subtitle="Freshness balanced with your taste" tracks={library.slice(12, 24)} play={play} like={like} add={add}/>
  </>;

  const discover = <><div className="page-hero"><div><span className="eyebrow">DISCOVERY ENGINE</span><h2>Follow the feeling.</h2><p>Radio, Vibe Journey, hidden gems and trend-aware discovery without leaving the NOMAD graph.</p></div><div className="quick-actions"><button onClick={buildRadio}><Icon name="spark"/> Smart Radio</button><button onClick={buildJourney}><Icon name="playlist"/> Vibe Journey</button></div></div><Rail title="Smart Radio" subtitle="Continuous recommendations around your current session" tracks={radio.length ? radio : recs} play={play} like={like} add={add}/><Rail title="Vibe Journey" subtitle="A 45-minute energy arc: chill → groove → peak → cooldown" tracks={journey} play={play} like={like} add={add}/><Rail title="Hidden Gems" subtitle="Lower-popularity candidates with strong taste similarity" tracks={library.slice(-12)} play={play} like={like} add={add}/></>;

  const ai = <><div className="page-hero ai-hero"><div><span className="eyebrow">NOMAD AI</span><h2>Talk to your music.</h2><p>The LLM interprets intent; deterministic music intelligence ranks, sequences and resolves the actual tracks.</p></div><div className="ai-badge"><Icon name="bot" size={28}/><span>Intent → Vibe Vector → Candidates → Score → Queue</span></div></div><div className="ai-grid"><section className="panel"><span className="eyebrow">VIBE MATCH</span><h3>What do you want to hear?</h3><textarea value={vibe} onChange={e => setVibe(e.target.value)} placeholder="dark cinematic night drive…"/><button className="primary" onClick={interpretVibe}><Icon name="spark"/> Interpret vibe</button>{vibeResult && <div className="vibe-result"><b>Parsed intent</b><pre>{JSON.stringify(vibeResult, null, 2)}</pre></div>}</section><section className="panel"><span className="eyebrow">INTELLIGENCE TOOLS</span><h3>Music operations</h3><button className="tool-row" onClick={buildRadio}><span><Icon name="spark"/></span><div><b>Smart Radio</b><small>Generate the next 18 tracks around the current seed.</small></div><Icon name="arrow"/></button><button className="tool-row" onClick={buildJourney}><span><Icon name="playlist"/></span><div><b>Energy Journey</b><small>Sequence a session with a controlled energy curve.</small></div><Icon name="arrow"/></button><button className="tool-row" onClick={() => flash("Playlist Doctor is wired for the next intelligence pass.")}><span><Icon name="settings"/></span><div><b>Playlist Doctor</b><small>Detect duplicates, gaps, repeated artists and energy jumps.</small></div><Icon name="arrow"/></button></section></div></>;

  let content: ReactNode = home;
  if (view === "Discover") content = discover;
  if (view === "AI / Vibe") content = ai;
  if (view === "Search") content = <><div className="page-hero compact"><div><span className="eyebrow">UNIFIED SEARCH</span><h2>Everything, one box.</h2><p>Provider fan-out, normalization and deduplication happen behind the scenes.</p></div></div>{results.length ? <TrackRows tracks={results} play={play} like={like} add={add}/> : <div className="empty"><Icon name="search" size={34}/><h3>Search your music</h3><p>Try an artist, track, album, genre or natural-language mood.</p></div>}</>;
  if (view === "Library") content = <><div className="page-hero compact"><div><span className="eyebrow">CANONICAL LIBRARY</span><h2>Your collection.</h2><p>Local files and connected sources collapse into one NOMAD Track graph.</p></div><div className="index-box"><input value={localRoot} onChange={e => setLocalRoot(e.target.value)} placeholder="C:\\Music"/><button onClick={indexLocal}>{busy ? "Indexing…" : "Index folder"}</button></div></div><TrackRows tracks={library} play={play} like={like} add={add}/></>;
  if (view === "Playlists") content = <><div className="page-hero compact"><div><span className="eyebrow">YOUR COLLECTION</span><h2>Playlists.</h2><p>Reference tracks, not audio files. The same playlist can resolve differently per device.</p></div><div className="new-playlist"><input value={newPlaylist} onChange={e => setNewPlaylist(e.target.value)} placeholder="New playlist name"/><button onClick={createPlaylist}><Icon name="plus"/></button></div></div><div className="playlist-grid">{playlists.map(p => <button key={p.id} className="playlist-tile" onClick={() => p.tracks[0] && play(p.tracks[0])}><img src={p.artwork_url || p.tracks[0]?.artwork_url || ""} alt=""/><div><b>{p.name}</b><span>{p.tracks.length} tracks</span></div></button>)}</div></>;

  return <div className="nomad-v4">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">N</div><div><b>NOMAD</b><span>MUSIC INTELLIGENCE</span></div></div><div className="status"><i/> <span>LOCAL ENGINE</span><b>ONLINE</b></div><nav>{NAV.map(([id, label], i) => <button key={id} className={view === id ? "active" : ""} onClick={() => setView(id)}><Icon name={["home", "search", "spark", "library", "playlist", "bot"][i]}/><span>{label}</span></button>)}</nav><div className="sidebar-bottom"><button className="source-hub" onClick={() => setShowSources(true)}><div><Icon name="globe"/><span>SOURCE HUB</span></div>{providers.slice(0, 3).map(p => <small key={p.name}><i className={p.connected || p.authenticated ? "good" : ""}/>{p.name} · {p.connected || p.authenticated ? "Connected" : p.mode === "public_metadata" ? "Ready" : "Offline"}</small>)}</button><div className="version">NOMAD V4 · UI FOUNDATION</div></div></aside>
    <main className="main"><header className="topbar"><div className="title"><span>NOMAD MUSIC</span><h1>{view === "Home" ? "Good evening" : view === "AI / Vibe" ? "NOMAD Intelligence" : view}</h1></div><div className="global-search"><Icon name="search"/><input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()} placeholder="Search songs, artists, albums…"/><kbd>Ctrl K</kbd><button onClick={search}>{busy ? "…" : "Search"}</button></div><button className="icon-btn"><Icon name="settings"/></button></header><div className="content">{content}</div></main>
    {toast && <div className="toast">{toast}</div>}
    <footer className="player"><div className="now"><div className="mini-art">{current?.artwork_url && <img src={current.artwork_url} alt=""/>}</div><div><b>{current?.title || "Nothing playing"}</b><span>{current?.artist_name || "Choose a track"}</span></div></div><div className="player-center"><div className="controls"><button onClick={() => move("previous")}><Icon name="prev"/></button><button className="main-play" onClick={toggle}>{queue?.is_playing ? <Icon name="pause"/> : <Icon name="play"/>}</button><button onClick={() => move("next")}><Icon name="next"/></button></div><div className="seek"><span>{fmt(position)}</span><input type="range" min="0" max={Math.max(duration, current?.duration_ms || 1)} value={Math.min(position, Math.max(duration, current?.duration_ms || 1))} onChange={e => seek(Number(e.target.value))}/><span>{fmt(duration || current?.duration_ms || 0)}</span></div></div><div className="player-right"><button className={queue?.shuffle ? "on" : ""} onClick={() => setMode("shuffle")}><Icon name="shuffle"/></button><button className={queue?.repeat !== "off" ? "on" : ""} onClick={() => setMode("repeat")}><Icon name="repeat"/></button><button onClick={() => current && loadLyrics(current)}><Icon name="lyrics"/></button><button onClick={() => setShowQueue(true)}><Icon name="queue"/></button><input className="volume" type="range" min="0" max="1" step=".01" value={queue?.volume ?? .8} onChange={e => volume(Number(e.target.value))}/></div></footer>
    {showQueue && <div className="overlay"><section className="drawer queue-drawer"><div className="drawer-head"><div><span className="eyebrow">UP NEXT</span><h3>Queue</h3></div><button onClick={() => setShowQueue(false)}><Icon name="close"/></button></div>{queue?.items?.map((item, i) => { const t = all.get(item.track_id); return <button className="queue-row" key={item.id} onClick={() => t && play(t)}><span>{String(i + 1).padStart(2, "0")}</span><img src={t?.artwork_url || ""} alt=""/><div><b>{t?.title || "Unknown track"}</b><small>{t?.artist_name || ""}</small></div></button>})}</section></div>}
    {showLyrics && <div className="overlay"><section className="drawer lyrics-drawer"><div className="drawer-head"><div><span className="eyebrow">LYRICS</span><h3>{current?.title || "Lyrics"}</h3></div><button onClick={() => setShowLyrics(false)}><Icon name="close"/></button></div><div className="lyrics-scroll">{lyrics.length ? lyrics.map((l, i) => <button key={`${l.time_ms}-${i}`} className={i === activeLyric ? "lyric active" : "lyric"} onClick={() => seek(l.time_ms)}>{l.text}</button>) : <div className="empty"><Icon name="lyrics" size={30}/><p>No synchronized lyrics available.</p></div>}</div></section></div>}
    {showSources && <div className="overlay"><section className="drawer source-drawer"><div className="drawer-head"><div><span className="eyebrow">SOURCE HUB</span><h3>Connected music</h3></div><button onClick={() => setShowSources(false)}><Icon name="close"/></button></div>{providers.map(p => <div className="provider-row" key={p.name}><span className="provider-dot"/><div><b>{p.name}</b><small>{p.account_name || p.mode}</small></div><strong>{p.connected || p.authenticated ? "Connected" : p.mode === "public_metadata" ? "Ready" : "Not connected"}</strong></div>)}</section></div>}
  </div>;
}
