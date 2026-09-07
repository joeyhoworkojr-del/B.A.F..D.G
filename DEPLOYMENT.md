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

## Configuration still required

Some parts of the product are deliberately switched off rather than faked.
Each one below names exactly what has to be configured to turn it on. Until
then the UI states the feature is unavailable and why, and the server refuses
the payload — nothing is hidden with CSS.

### 1. Durable storage (blocks accounts, alerts, watchlists)

**The code is ready; the database is not provisioned.** The ledger now runs on
either backend: SQLite by default, Postgres as soon as `DATABASE_URL` is set.
Nothing else needs changing — set the variable and the record becomes durable.

Until then the record is SQLite on the container's own disk, which Fly replaces
on every deploy, so it silently restarts each release. The Results page says so
in an amber notice, and `/api/v1/accuracy` reports `storage_durable: false`.

To make it durable, either:

- **Managed Postgres (recommended).** Create one (Neon, Supabase, or
  `fly postgres create`) and set `DATABASE_URL` to its connection string:
  `fly secrets set DATABASE_URL='postgresql://...' --app statedge-api`.
  The schema is created on first connect; no migration step to run.
- **A Fly volume.** Mount one, set `LEDGER_PATH=/data/ledger.db`, and set
  `LEDGER_DURABLE=1` so the UI stops warning. Note the history below.
- Two previous attempts to attach a volume to this app failed
  (`insufficient resources to create new machine with existing volume` in
  `dfw`), and the automated migration took the app down because it destroyed
  the volume-less machine first. If you retry, **create the new machine
  before destroying the old one**, and be ready to fall back to a different
  region or to Postgres.

Nothing that needs to survive a deploy should be built until this is settled.

### 2. Authentication (blocks user accounts)

There is no auth in the app and no mock standing in for it: no sign-in form,
no password storage, and nothing in `localStorage` pretending to be a session.

Required:

- A provider-managed identity service that owns credentials, sessions and
  password resets (Auth0, Clerk, WorkOS, Supabase Auth or similar). StatEdge
  must never store passwords itself.
- `AUTH_PROVIDER` set to the integration name, plus that provider's issuer,
  audience and signing-key settings.
- Durable storage from §1, so an account survives the next release.

Once `AUTH_PROVIDER` is set, `resolve_entitlements()` in
`backend/src/api/routes/account.py` is the single place that reads the
caller's session; no route that consumes it needs to change.

### 3. Player-props odds provider (blocks the Props section)

ESPN's keyless feed publishes no player-prop lines, so `GET /api/v1/props`
reports `available=false` and lists its requirements.

Required:

- A licensed player-props odds provider with NFL and NCAA football player
  markets (The Odds API, OddsJam, or a sportsbook partner feed).
- `PROPS_PROVIDER` naming the integration and `PROPS_API_KEY` holding the
  credential.
- Player-level projections from the model. The gridiron engine currently
  projects team scores and game totals only, so props would need new
  modelling work, not just a feed.

### 4. Push and email alerts

The in-app notification centre works today and lists the graded edges the
model is currently publishing. Delivering alerts off-site needs an account to
deliver them to, so this is blocked on §1 and §2.

### 5. Billing

Not implemented, and deliberately so — this release is free. Entitlements
already resolve server-side with `billing_enabled=false`, so a paid tier can
be introduced later without changing how features are gated.

## Environment variables added in this release

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTH_PROVIDER` | *(unset)* | Names the identity provider. While unset, `/api/v1/entitlements` reports `auth_configured=false` and every caller is anonymous on the free plan. |
| `PROPS_PROVIDER` | *(unset)* | Names the player-props odds integration. |
| `PROPS_API_KEY` | *(unset)* | Credential for that provider. |

## Vercel (frontend) + Fly (API)

The SPA is deployed from Vercel's GitHub integration; the API stays on Fly,
where the snapshot loop and the in-process ESPN caches keep working. No Vercel
token is involved — Vercel builds from the repo.

Project settings that matter:

- **Root Directory: either setting works.** There are two `vercel.json` files
  and Vercel reads whichever matches the configured root: the one at the repo
  root builds `frontend/` explicitly, the one in `frontend/` builds in place.
  Their `rewrites` and `headers` are identical and must be kept in sync — a
  test asserts it.
- **The custom domain serves `main`.** Preview deployments get their own URL;
  `statedge.ca` only changes when a commit lands on the production branch.
- **No `VITE_API_BASE` needed.** The app is same-origin by default and
  `vercel.json` rewrites `/api/*` and `/health` to
  `https://statedge-api.fly.dev`, so the browser never makes a cross-origin
  request and CORS never applies. Set `VITE_API_BASE` only if you deliberately
  want the bundle to call the Fly host directly.
- If you do set it to the absolute Fly URL, CORS covers Vercel already:
  `CORS_ORIGIN_REGEX` defaults to `https://.*\.vercel\.app`, which matches
  preview deployments too. A custom domain needs adding to `CORS_ORIGINS`.

Changing the API host means editing the two rewrite destinations in
`frontend/vercel.json`.

### What does *not* move

The API cannot go serverless as-is without replacing two things first:

- The snapshot loop in `src/api/main.py` runs in the FastAPI lifespan and only
  exists while a long-lived process does. On serverless it stops silently and
  the track record stops recording. It would need a scheduled invocation of a
  `/internal/snapshot` route instead.
- The SQLite ledger would land on per-instance `/tmp`, so the record would
  fragment across instances — worse than today's single ephemeral copy.
  Postgres is a prerequisite, not an optimisation.
