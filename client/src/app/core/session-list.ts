/** Server times are UTC but come without a "Z" (e.g. 2026-11-18T14:02:11.123456). Make that explicit before parsing. */
export function parseUtc(iso: string): Date {
  const hasZone = /[zZ]$|[+-]\d{2}:\d{2}$/.test(iso);
  return new Date(hasZone ? iso : iso + 'Z');
}

/** "just now", "12 min ago", "3 h ago", "2 days ago". Future times (clock drift) count as "just now". */
export function signedInAgo(createdAt: string, now: Date): string {
  const mins = Math.floor((now.getTime() - parseUtc(createdAt).getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

/** "7 h 12 min left", "45 min left", "less than a minute left", or "expired". */
export function timeLeft(expiresAt: string, now: Date): string {
  const mins = Math.floor((parseUtc(expiresAt).getTime() - now.getTime()) / 60000);
  if (mins < 0) return 'expired';
  if (mins < 1) return 'less than a minute left';
  if (mins < 60) return `${mins} min left`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h} h left` : `${h} h ${m} min left`;
}
