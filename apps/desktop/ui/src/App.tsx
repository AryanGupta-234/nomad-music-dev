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

// Existing NOMAD library rows may contain an older 300px Spotify image URL.
// Spotify's Web API exposes album images in multiple sizes, so upgrade the
// known 300px CDN variant to the 640px source when the URL format allows it.
function highResArtwork(url?: string | null) {
  if (!url) return undefined;
  if (url.includes("i.scdn.co/image/")) {
    return url.replace("ab67616d00001e02", "ab67616d0000b273");
  }
  return url;
}

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
  function artStyle(t?: Track | null) { const url = highResArtwork(t?.artwork_url); return url ? { backgroundImage: `url(${url})` } : undefined; }
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
