# Deploying StatEdge

Two supported paths: **Fly.io** (public production deploy, auto-deploys from
GitHub once set up) and **docker compose** (any VPS or local machine).

## Fly.io — one-time setup (~5 minutes)

1. Install the CLI and sign in:

   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth signup        # or: fly auth login
   ```

2. Create the two apps (names must match the `app =` lines in
   `backend/fly.toml` and `frontend/fly.toml` — change both if taken):

   ```bash
   fly apps create statedge-api
   fly apps create statedge-frontend
   ```

3. First deploy, from the repo root:

   ```bash
   make deploy          # runs fly deploy in backend/ then frontend/
   ```

   The site comes up at `https://statedge-frontend.fly.dev`, talking to
   `https://statedge-api.fly.dev`. The API runs fine with no secrets —
   database/Redis are optional, and weather works keyless via Open-Meteo.
   Optional extras:

   ```bash
   fly secrets set FOOTBALL_DATA_API_KEY=... --app statedge-api   # live scores
   ```

4. **Auto-deploy on every push to `main`** — create a deploy token and add it
   to GitHub:

   ```bash
   fly tokens create deploy
   ```

   Copy the output into the repo: Settings → Secrets and variables → Actions →
   New repository secret, name `FLY_API_TOKEN`. From then on,
   `.github/workflows/fly-deploy.yml` tests and ships both apps on every push
   to `main`.

   If you renamed the apps, also update `VITE_API_BASE` in
   `frontend/fly.toml` and `CORS_ORIGINS` in `backend/fly.toml` so the two
   sides point at each other.

## docker compose — self-hosted

```bash
make dev        # copies .env.example → .env and runs docker compose up --build
```

- Frontend: http://localhost:5173 (nginx, proxies `/api/` to the backend)
- API + docs: http://localhost:8000/docs
- Postgres + Redis + Celery worker/beat included.

## How the pieces fit

- The frontend bakes `VITE_API_BASE` at **build** time. `/` (default) means
  same-origin — nginx proxies `/api/` to the `api` service (compose). On Fly,
  `frontend/fly.toml` overrides it to the public API URL and the browser calls
  the API directly, so `CORS_ORIGINS` on the API must include the frontend
  origin.
- `frontend/nginx.conf` is an nginx *template*: `API_UPSTREAM` and
  `NGINX_RESOLVER` are substituted at container start, and the upstream is
  resolved per-request — so the same image boots on platforms where the
  compose hostname `api` doesn't exist.
