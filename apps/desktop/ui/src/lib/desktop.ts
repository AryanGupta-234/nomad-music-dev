import { openUrl } from '@tauri-apps/plugin-opener';

export function isTauri(): boolean {
  return typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);
}

export async function openExternal(url: string): Promise<void> {
  if (isTauri()) {
    await openUrl(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

export async function waitForNomadApi(base = 'http://127.0.0.1:8765/api/v1', attempts = 60): Promise<boolean> {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const r = await fetch(`${base}/health`);
      if (r.ok) return true;
    } catch (_) {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}
