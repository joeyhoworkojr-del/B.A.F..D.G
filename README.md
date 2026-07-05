# StatEdge — a stock market for sports analytics

Live at **https://statedge-api.fly.dev**

StatEdge prices every game three ways — **our model**, **the sportsbook**, and
**the Polymarket crowd** — and shows you where they disagree. Every prediction
is snapshotted before kickoff and auto-graded against the final score, so the
track record is verifiable, not vibes.

## What it does

- **Four sports, one engine surface** — MLB (Poisson run grid with park
  factors and starting pitchers), NFL and CFL (expected-points engine with
  Normal margin/total distributions), and international soccer (Dixon-Coles
  Poisson with team styles).
- **Live market board** — scores, spreads, totals, and moneylines from ESPN's
  public feed, refreshed every minute, date-windowed so yesterday's finals
  never masquerade as today's games.
- **Crowd signal** — real-money Polymarket prices and volume matched to each
  game, so you can compare the model with where the public's money actually is.
- **Live conditions** — Open-Meteo stadium weather and lineup/injury toggles
  re-price predictions instantly.
- **Value math** — vig removal, expected value, edge ratings (A/B/C), and
  quarter-Kelly stake sizing on every priced market.
- **Verified track record** — pre-game snapshots of model/book/crowd graded
  automatically at the final whistle; Brier scores head-to-head plus honest
  P/L betting the model's pick at the book's no-vig price (`/track`).

## Stack

| Layer    | Tech |
|----------|------|
| Backend  | FastAPI, Python 3.12, SQLite ledger (stdlib only) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Deploy   | Single Docker image (SPA baked into the API container), Fly.io, GitHub Actions auto-deploy on merge to `main` |
| Data     | ESPN public scoreboards · Open-Meteo · Polymarket Gamma API — all keyless, all fail-safe |

## Development

```bash
# Backend (http://localhost:8000, docs at /docs)
cd backend
pip install -e ".[dev]"
PYTHONPATH=. uvicorn src.api.main:app --reload

# Frontend (http://localhost:5173)
cd frontend
npm install
npm run dev

# Tests
cd backend && PYTHONPATH=. python -m pytest tests/ -q
cd frontend && npm run type-check && npm run build
```

To serve the built SPA from the API (production layout):
`STATIC_DIR=../frontend/dist` when starting uvicorn.

Set `LEDGER_PATH=/data/ledger.db` (with a mounted volume) to persist the
track record across deploys — see `DEPLOYMENT.md`.

> For information and entertainment only. Not betting advice.
