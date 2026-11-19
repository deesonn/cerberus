# Running Cerberus with Docker

Two containers, started together by `docker-compose.yml`:

| Container | Built from | Job |
|---|---|---|
| `backend` | `backend/Dockerfile` | The FastAPI server (uvicorn on port 8000, not published to the host). Runs as a non-root user. Its SQLite database lives in the `cerberus-data` volume, so it survives restarts and rebuilds. |
| `web` | `client/Dockerfile` | Builds the Angular app, then serves it with nginx on port 80 (published as **8080**). nginx also forwards `/api/...` to the backend with the `/api` prefix removed. |

The browser only talks to `web`. Because the API is reached at `/api` on the same origin, there's no CORS to configure and no API address baked into the build.

## Start it

```bash
docker compose up --build            # first run builds both images
# in another terminal, make the first administrator inside the running backend:
docker compose exec backend python -m app.cli create-admin daniel
# then open http://localhost:8080 and sign in
```

Other accounts: `docker compose exec backend python -m app.cli create-user someone`, or use the Admin page.

## Settings

Set them under `backend: environment:` in `docker-compose.yml`:

| Variable | Default | Meaning |
|---|---|---|
| `CERBERUS_SESSION_HOURS` | `8` | Login lifetime |
| `CERBERUS_QUOTA_MB` | `200` | Storage per account |
| `CERBERUS_DB_URL` | `sqlite:////data/cerberus.db` | Keep it under `/data` so it stays in the volume |

## Stop, back up, reset

```bash
docker compose down                  # stop; data stays in the volume
docker compose down -v               # stop AND delete the database volume
docker run --rm -v cerberus_cerberus-data:/data -v "$PWD":/backup alpine cp /data/cerberus.db /backup/cerberus-backup.db
```

## What has and hasn't been tested

- `docker compose config` validates the compose file.
- The same-origin `/api` setup was tested in a real browser using `e2e/prod_proxy.py`, a small stand-in for nginx that does the same two jobs (serve the built client with a fallback to `index.html`, forward `/api/` with the prefix stripped). Run `python e2e/e2e_week4.py http://localhost:8080` against it.
- The images themselves have **not** been built in the environment this was written in (no Docker daemon was available there), so the first `docker compose up --build` on a machine with Docker is the real test of the Dockerfiles and `nginx.conf`.
