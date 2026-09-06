# Deploying StatEdge

StatEdge ships as **one app**: the FastAPI backend serves the API under
`/api/v1` and the built React site on every other route. One image, one
deploy, one URL, no CORS.

Two supported paths: **Fly.io** (public production deploy, auto-deploys from
GitHub once set up) and **docker compose** (any VPS or local machine).

## Fly.io — one-time setup (~5 minutes)

1. Install the CLI and sign in:

   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth signup        # or: fly auth login
   ```

2. Create the app (the name must match the `app =` line in the root
   `fly.toml` — if `statedge-api` is taken, pick another and update it):

   ```bash
   fly apps create statedge-api
   ```

3. First deploy, from the repo root:

   ```bash
   make deploy        # = fly deploy
   ```

   The whole site comes up at `https://statedge-api.fly.dev` — pages and API
   from the same host. No secrets required to run: database/Redis are
   optional and weather works keyless via Open-Meteo. Optional extras:

   ```bash
   fly secrets set FOOTBALL_DATA_API_KEY=... --app statedge-api   # live scores
   ```

4. **Auto-deploy on every push to `main`** — create a deploy token and add it
   to GitHub:

   ```bash
   fly tokens create deploy
   ```

   Copy the full output (one line, starts with `FlyV1 `) into the repo:
   Settings → Secrets and variables → Actions → New repository secret, name
   `FLY_API_TOKEN`. From then on, `.github/workflows/fly-deploy.yml` tests
   and ships the app on every push to `main`.

## Persisting the track record (automated on Fly)

The verified track record + self-correcting ratings live in a SQLite file, made
durable by a Fly volume: `fly.toml` mounts `statedge_data` at `/data` and sets
`LEDGER_PATH=/data/ledger.db`.

Fly **cannot attach a volume to an already-running machine in place**, so the
deploy workflow handles the migration itself (in the `deploy` job, before
`flyctl deploy`):

```yaml
- name: Ensure ledger volume + migrate machine
  run: |
    # Create the volume in the primary region if it isn't there yet.
    flyctl volumes list --app statedge-api --json \
      | jq -e '.[] | select(.name=="statedge_data" and .state!="destroyed")' >/dev/null \
      || flyctl volumes create statedge_data --app statedge-api --region dfw --size 1 --yes
    # Destroy any machine that has no mount so the deploy recreates it WITH the
    # volume. Idempotent — once machines are mounted, nothing is destroyed.
    for id in $(flyctl machines list --app statedge-api --json \
                | jq -r '.[] | select((.config.mounts // []) | length == 0) | .id'); do
      flyctl machine destroy "$id" --force || true
    done
```

The **first** deploy after this lands has a brief blip while the machine is
recreated on the volume; every deploy after that is a normal in-place update and
the record persists. Predictions snapshot themselves whenever a slate loads and
grade themselves as games go final, so the ledger fills in on its own.

## docker compose — self-hosted

```bash
make dev        # copies .env.example → .env and runs docker compose up --build
```

- Frontend: http://localhost:5173 (nginx, proxies `/api/` to the backend)
- API + docs: http://localhost:8000/docs
- Postgres + Redis + Celery worker/beat included.

## How the single-app image works

- The root `Dockerfile` builds the React app with `VITE_API_BASE=/`
  (same-origin) and copies `dist/` into the backend image at `/app/static`.
- `src/api/main.py` mounts that directory when it exists: `/assets/*` are
  served as files, unknown non-API paths fall back to `index.html` so
  client-side routes (`/nfl`, `/best-bets`) survive refreshes, and unknown
  `/api/*` paths still 404.
- Run locally without Docker: `make dev-backend` serves the API alone, or
  set `STATIC_DIR=frontend/dist` after `npm run build` to serve both.
