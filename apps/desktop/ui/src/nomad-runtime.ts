/* NOMAD runtime bridge.
 * Keeps provider playback inside the desktop WebView when a provider returns
 * a YouTube watch URL/video id. The React player historically called
 * window.open(), which escaped to an external browser and made the in-app
 * player appear stuck. We intercept only YouTube playback URLs and render a
 * compact first-party iframe surface; all other window.open calls are left
 * untouched.
 */

function youtubeId(value: string): string | null {
  try {
    const raw = value.trim();
    if (/^[A-Za-z0-9_-]{11}$/.test(raw)) return raw;
    const url = new URL(raw);
    if (url.hostname === "youtu.be") return url.pathname.slice(1).split("/")[0] || null;
    if (url.hostname.endsWith("youtube.com")) {
      if (url.pathname === "/watch") return url.searchParams.get("v");
      const parts = url.pathname.split("/").filter(Boolean);
      if (parts[0] === "embed" || parts[0] === "shorts") return parts[1] || null;
    }
  } catch { /* not a URL; caller may have supplied an id */ }
  return null;
}

function closePlayer() {
  document.getElementById("nomad-youtube-player")?.remove();
}

function openPlayer(target: string) {
  const id = youtubeId(target);
  if (!id) return false;
  closePlayer();

  const shell = document.createElement("div");
  shell.id = "nomad-youtube-player";
  shell.innerHTML = `
    <div class="nomad-yt-head">
      <span><i></i> YouTube playback</span>
      <button type="button" aria-label="Close">×</button>
    </div>
    <div class="nomad-yt-frame-wrap">
      <iframe
        src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&playsinline=1&rel=0&modestbranding=1"
        title="NOMAD YouTube playback"
        allow="autoplay; encrypted-media; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>`;
  shell.querySelector("button")?.addEventListener("click", closePlayer);
  document.body.appendChild(shell);
  return true;
}

const originalOpen = window.open.bind(window);
window.open = ((url?: string | URL, target?: string, features?: string) => {
  const value = String(url ?? "");
  if (value.includes("youtube.com") || value.includes("youtu.be") || youtubeId(value)) {
    if (openPlayer(value)) return null;
  }
  return originalOpen(url, target, features);
}) as typeof window.open;

export {};
