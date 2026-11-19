import { FileMeta } from './files.service';

export type SortKey = 'newest' | 'oldest' | 'name' | 'size';

/** 0 -> "0 B", 1536 -> "1.5 KB", 26214400 -> "25 MB". Uses 1024 steps, same as the server's 25 MB cap. */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  const text = i === 0 || value >= 10 ? Math.round(value).toString() : value.toFixed(1).replace(/\.0$/, '');
  return `${text} ${units[i]}`;
}

/** Case-insensitive "contains" on the filename; blank search returns everything. Never changes the input array. */
export function filterFiles(files: FileMeta[], search: string): FileMeta[] {
  const needle = search.trim().toLowerCase();
  if (!needle) return files.slice();
  return files.filter((f) => f.filename.toLowerCase().includes(needle));
}

/** Returns a sorted copy. Ties fall back to filename so the order is always stable. */
export function sortFiles(files: FileMeta[], key: SortKey): FileMeta[] {
  const byName = (a: FileMeta, b: FileMeta) => a.filename.localeCompare(b.filename, undefined, { sensitivity: 'base' });
  const time = (f: FileMeta) => new Date(f.uploaded_at).getTime();
  const copy = files.slice();
  switch (key) {
    case 'oldest': return copy.sort((a, b) => time(a) - time(b) || byName(a, b));
    case 'name':   return copy.sort(byName);
    case 'size':   return copy.sort((a, b) => b.size - a.size || byName(a, b));
    default:       return copy.sort((a, b) => time(b) - time(a) || byName(a, b));
  }
}

/** Percentage of the quota used, clamped to 0-100 and safe when the quota is 0. */
export function percentUsed(used: number, quota: number): number {
  if (!quota || quota <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((used / quota) * 100)));
}

export const MAX_FILENAME_LENGTH = 255;

export type NameCheck = { ok: true; value: string } | { ok: false; error: string };

/** The same rules the server applies to upload and rename, checked first so the person gets an instant, plain message. */
export function cleanFilename(raw: string): NameCheck {
  const value = raw.trim();
  if (!value) return { ok: false, error: "The name can't be empty." };
  if (value.length > MAX_FILENAME_LENGTH) return { ok: false, error: `The name is too long (${MAX_FILENAME_LENGTH} characters at most).` };
  if (/[\\/]/.test(value) || /[\u0000-\u001f\u007f]/.test(value)) return { ok: false, error: "The name can't contain slashes." };
  return { ok: true, value };
}
