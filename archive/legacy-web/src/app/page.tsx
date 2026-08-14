"use client";

import { useEffect, useMemo, useState } from "react";

type Source = { provider: string; provider_id: string; playback_kind?: string | null };
type Track = { id: string; title: string; duration_ms?: number | null; artwork_url?: string | null; sources?: Source[] };
type Playlist = { id: string; name: string; description?: string | null; tracks: Track[] };

const API = process.env.NEXT_PUBLIC_NOMAD_API || "http://127.0.0.1:8000/api/v1";
const nav = ["Home", "Search", "Discover", "Library", "Playlists", "AI / Vibe"];

export default function Home() {
  const [active, setActive] = useState("Home");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Track[]>([]);
  const [library, setLibrary] = useState<Track[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [recommendations, setRecommendations] = useState<{ track_id: string; score: number; reason: Record<string, number> }[]>([]);
  const [providers, setProviders] = useState<{ name: string; configured: boolean; mode: string }[]>([]);
  const [vibe, setVibe] = useState("dark cinematic night drive, more discovery");
  const [vibeResult, setVibeResult] = useState<string>("");
  const [nowPlaying, setNowPlaying] = useState<Track | null>(null);
  const [busy, setBusy] = useState(false);

  const recMap = useMemo(() => new Map(library.map((t) => [t.id, t])), [library]);

  async function refresh() {
    const [lib, pls, rec, health] = await Promise.all([
      fetch(`${API}/library?limit=30`).then((r) => r.json()),
      fetch(`${API}/playlists`).then((r) => r.json()),
      fetch(`${API}/recommendations?limit=8`).then((r) => r.json()),
      fetch(`${API}/health/providers`).then((r) => r.json()),
    ]);
    setLibrary(lib.tracks || []);
    setPlaylists(Array.isArray(pls) ? pls : []);
    setRecommendations(rec.results || []);
    setProviders(health.providers || []);
  }

  async function search() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      const d = await fetch(`${API}/search?q=${encodeURIComponent(query)}&limit=24`).then((r) => r.json());
      setResults((d.results || []).map((x: { track: Track }) => x.track));
      setActive("Search");
    } finally { setBusy(false); }
  }

  async function interpretVibe() {
    const d = await fetch(`${API}/vibe?q=${encodeURIComponent(vibe)}`).then((r) => r.json());
    setVibeResult(JSON.stringify(d.query, null, 2));
    setActive("AI / Vibe");
  }

  async function syncSearch() {
    if (!query.trim()) return;
    setBusy(true);
    try {
      await fetch(`${API}/search/sync?query=${encodeURIComponent(query)}&limit=20`, { method: "POST" });
      await refresh();
      await search();
    } finally { setBusy(false); }
  }

  useEffect(() => { refresh().catch(() => undefined); }, []);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">N</div><div><div className="brand-name">NOMAD</div><div className="brand-sub">Music Intelligence</div></div></div>
        <nav>{nav.map((item) => <button key={item} className={`nav ${active === item ? "active" : ""}`} onClick={() => setActive(item)}><span className="nav-glyph">{item === "Home" ? "⌂" : item === "Search" ? "⌕" : item === "Discover" ? "✦" : item === "Library" ? "♫" : item === "Playlists" ? "▣" : "◎"}</span>{item}</button>)}</nav>
        <div className="provider-mini"><div className="mini-label">PROVIDERS</div>{providers.map((p) => <div className="provider-row" key={p.name}><span className={p.configured ? "dot on" : "dot"}/>{p.name}<small>{p.configured ? "ready" : "waiting"}</small></div>)}</div>
        <div className="sidebar-foot">Local-first · API v1</div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div><div className="eyebrow">UNIFIED MUSIC INTELLIGENCE</div><h1>{active === "Home" ? "Good evening." : active}</h1><p>One canonical music graph across your connected sources.</p></div>
          <div className="search"><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} placeholder="Search songs, artists, albums, playlists…"/><button onClick={search}>{busy ? "…" : "Search"}</button></div>
        </header>

        {active === "Home" && <>
          <section className="hero-card"><div className="hero-glow"/><div className="hero-copy"><span className="pill">NOMAD CORE · LOCAL-FIRST</span><h2>Your music, understood.</h2><p>Spotify, YouTube, local music and discovery sources become one canonical library. The recommender learns from your behavior; the LLM only translates your intent.</p><div className="hero-actions"><button className="primary" onClick={interpretVibe}>Try Vibe Match</button><button className="secondary" onClick={() => setActive("Library")}>Open Library</button></div></div><div className="vibe-card"><div className="mini-label">CURRENT VIBE</div><div className="vibe-title">Late Night Focus</div><div className="bars">{[25,48,35,74,60,94,72,82].map((h, i) => <i style={{height:`${h}%`}} key={i}/>)}</div><div className="vibe-meta">dark · focused · 108–124 BPM</div></div></section>
          <section className="grid"><Panel title="Made For You" subtitle="Persistent recommendation candidates" wide>{recommendations.length ? recommendations.slice(0,6).map((r) => { const t=recMap.get(r.track_id); return <TrackRow key={r.track_id} t={t} onPlay={setNowPlaying} meta={`score ${r.score.toFixed(2)}`}/>; }) : <Empty text="Keep listening; the recommendation pool will build here."/>}</Panel><Panel title="Your Library" subtitle={`${library.length} indexed tracks`}>{library.slice(0,6).map(t => <TrackRow key={t.id} t={t} onPlay={setNowPlaying} />) || <Empty text="Nothing indexed yet."/>}</Panel><Panel title="Playlists" subtitle="Reference-based, provider-agnostic">{playlists.slice(0,5).map(p => <div key={p.id} className="playlist-row"><div className="cover mini"/><div><b>{p.name}</b><span>{p.tracks.length} tracks</span></div></div>) || <Empty text="Create your first playlist."/>}</Panel></section>
        </>}

        {active === "Search" && <section className="panel wide"><div className="panel-head"><div><h3>Search</h3><span>Local graph first, provider enrichment second</span></div><button className="secondary compact" onClick={syncSearch}>Sync this query</button></div><div className="tracks">{results.length ? results.map(t => <TrackRow key={t.id} t={t} onPlay={setNowPlaying}/>) : <Empty text="Search for a track, artist, album or vibe."/>}</div></section>}

        {active === "Library" && <section className="panel wide"><div className="panel-head"><div><h3>Your Library</h3><span>Canonical tracks, independent of source</span></div></div><div className="tracks">{library.length ? library.map(t => <TrackRow key={t.id} t={t} onPlay={setNowPlaying}/>) : <Empty text="Your library is empty."/>}</div></section>}

        {active === "Playlists" && <section className="playlist-grid">{playlists.map(p => <article className="playlist-card" key={p.id}><div className="playlist-art"/><div className="playlist-info"><div className="eyebrow">PLAYLIST</div><h2>{p.name}</h2><p>{p.description || "A NOMAD playlist."}</p><span>{p.tracks.length} tracks</span></div><div className="playlist-tracks">{p.tracks.slice(0,4).map(t => <TrackRow key={t.id} t={t} onPlay={setNowPlaying}/>)}</div></article>)}{!playlists.length && <Empty text="Create your first playlist with NOMAD."/>}</section>}

        {active === "Discover" && <section className="grid"><Panel title="New For You" subtitle="Provider data prepared by the background engine" wide><Empty text="Release radar will populate here once provider sync is connected."/></Panel><Panel title="Hidden Gems" subtitle="Low exposure, high fit"><Empty text="Candidate discovery will populate here."/></Panel><Panel title="Global" subtitle="Charts and regional discovery"><Empty text="Global discovery is queued for provider enrichment."/></Panel></section>}

        {active === "AI / Vibe" && <section className="grid"><Panel title="NOMAD AI" subtitle="Intent layer — not the recommender" wide><textarea value={vibe} onChange={e => setVibe(e.target.value)} placeholder="Describe what you want to hear…"/><button className="full" onClick={interpretVibe}>Interpret vibe</button>{vibeResult && <pre className="json">{vibeResult}</pre>}</Panel><Panel title="Signature flows" subtitle="The next intelligence layer"><div className="chip-grid">{["Vibe Match","Smart Radio","Vibe Journey","Playlist Doctor","AI DJ","Why This?"].map(x => <button key={x} className="chip">{x}</button>)}</div></Panel></section>}
      </section>

      <div className="player"><div className="player-art"/ ><div className="player-text"><b>{nowPlaying?.title || "Nothing playing"}</b><span>{nowPlaying ? "Ready to resolve from the canonical graph" : "Select a track to begin"}</span></div><div className="player-controls"><button>◀</button><button className="playbig">▶</button><button>▶</button></div><div className="player-status">{nowPlaying ? (nowPlaying.sources?.[0]?.provider || "NOMAD") : "NOMAD"}</div></div>
    </main>
  );
}

function Panel({title, subtitle, children, wide=false}:{title:string;subtitle:string;children:React.ReactNode;wide?:boolean}) { return <div className={`panel ${wide ? "wide" : ""}`}><div className="panel-head"><div><h3>{title}</h3><span>{subtitle}</span></div></div>{children}</div>; }
function Empty({text}:{text:string}) { return <div className="empty">{text}</div>; }
function TrackRow({t,onPlay,meta}:{t?:Track;onPlay:(t:Track)=>void;meta?:string}) { if(!t) return null; return <div className="track"><div className="cover" style={t.artwork_url?{backgroundImage:`url(${t.artwork_url})`,backgroundSize:"cover"}:{}}/><div className="track-main"><strong>{t.title}</strong><span>{meta || (t.sources || []).map(s=>s.provider).join(" · ") || "Canonical NOMAD track"}</span></div><div className="sources">{(t.sources || []).slice(0,3).map(s => <small key={`${s.provider}-${s.provider_id}`}>{s.provider}</small>)}</div><button className="play" onClick={()=>onPlay(t)}>▶</button></div>; }
