/**
 * Where the API lives.
 * - `ng serve` (port 4200) talks straight to the dev API on port 8000.
 * - Anything else (the Docker/nginx deployment) uses the same origin under /api, so no CORS and no hardcoded host.
 */
export function apiBase(loc: { port: string; hostname: string }): string {
  return loc.port === '4200' ? `http://${loc.hostname}:8000` : '/api';
}
