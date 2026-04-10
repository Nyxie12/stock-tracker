# Stock Tracker

A real-time stock tracking app with watchlists, price alerts, charts, a market heatmap, and paper trading.

## Stack

**Backend** (`backend/`) — FastAPI + SQLAlchemy async
- Python, FastAPI 0.115, SQLAlchemy 2.0 async, Alembic, Pydantic v2
- SQLite via `aiosqlite` (default: `./stocktracker.db`)
- Market data: Finnhub (REST + WebSocket stream), yfinance, vaderSentiment for news sentiment
- Entry: `backend/app/main.py` — lifespan wires up `FinnhubStream`, `FinnhubClient`, `ConnectionManager`, `AlertEngine`, `HeatmapService`

**Frontend** (`frontend/`) — React 19 + Vite + TypeScript
- React Router 7, TanStack Query, Zustand, Tailwind
- Charts: `lightweight-charts`, `recharts`, `d3-hierarchy` (heatmap treemap)

## Layout

```
backend/app/
  main.py              # FastAPI app + lifespan
  config.py            # Settings (env: FINNHUB_API_KEY, DATABASE_URL, CORS_ORIGINS, TICK_THROTTLE_MS)
  db.py                # Async engine, SessionLocal, init_models
  models/              # alert, paper, watchlist, base
  routers/             # watchlist, profile, candles, heatmap, alerts, paper, debug, ws
  schemas/
  services/            # alert_engine, connection_manager, finnhub_client, finnhub_stream,
                       # heatmap, paper_trading, yfinance_service
  utils/
backend/alembic/versions/
backend/tests/

frontend/src/
  App.tsx, main.tsx
  pages/               # WatchlistPage, ChartsPage, HeatmapPage, AlertsPage, PaperTradingPage, NewsPage
  components/          # TickerTable, PriceChart, Sparkline, Heatmap, AlertForm, TimeframeToggle
  stores/              # tickerStore, alertStore (Zustand)
  api/  hooks/  lib/
```

## Running

**Backend**
```bash
cd backend
pip install -r requirements.txt
# create .env with FINNHUB_API_KEY=...
uvicorn app.main:app --reload
```
- Health check: `GET /api/health`
- WebSocket router at `app/routers/ws.py` broadcasts ticks via `ConnectionManager`

**Frontend**
```bash
cd frontend
npm install
npm run dev        # Vite dev server (default http://localhost:5173)
npm run build      # tsc -b && vite build
npm run lint
```

## Key concepts

- **Tick flow**: `FinnhubStream` → `_on_tick` callback in `main.py` → `AlertEngine.on_tick` (evaluates rules) + `ConnectionManager.broadcast_tick` (pushes to WS clients). Throttled by `tick_throttle_ms`.
- **Alerts**: persisted via `models/alert.py`; `AlertEngine.load_from_db()` rehydrates on startup.
- **Heatmap**: `HeatmapService` in `services/heatmap.py`, exposed via `routers/heatmap.py`.
- **Paper trading**: `services/paper_trading.py` + `models/paper.py` + `routers/paper.py`.

## Config

Env vars (via `backend/.env`, loaded by `pydantic-settings`):
- `FINNHUB_API_KEY` — required for live data
- `DATABASE_URL` — default `sqlite+aiosqlite:///./stocktracker.db`
- `CORS_ORIGINS` — comma-separated, default `http://localhost:5173`
- `TICK_THROTTLE_MS` — default 500
- `DEBUG` — default true
- `JWT_SECRET_KEY` — JWT signing secret. Has a dev default; **must** be overridden in production.
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default 7 days.

## Auth

Email/password accounts with JWT bearer tokens. All data routers (`watchlist`,
`alerts`, `paper`) and the `/ws` WebSocket require a valid token; every row in
`watchlists`, `alerts`, `paper_portfolios` is scoped by `user_id`. Token is
stored in `localStorage` on the frontend and injected as `Authorization:
Bearer …` by `frontend/src/api/client.ts`. The WS connects with
`?token=<jwt>`; a 1008 close triggers a frontend logout.

Key files: `backend/app/models/user.py`, `backend/app/routers/auth.py`,
`backend/app/utils/security.py`, `backend/app/deps.py`,
`frontend/src/stores/authStore.ts`, `frontend/src/components/RequireAuth.tsx`.

**Note:** The schema changed — if you have a pre-auth `backend/stocktracker.db`
it must be deleted before first run (the repo keeps one such file named
`stocktracker.db.pre-auth-backup`).

## Current status / next steps

Project is being built in **phases**. Inferred from the code:

**Done (Phases 1–5)**
- Backend scaffold: FastAPI app, async SQLAlchemy, config, CORS, lifespan wiring.
- Finnhub integration: `FinnhubClient` (REST) and `FinnhubStream` (WebSocket) with tick throttling + fan-out via `ConnectionManager`.
- WebSocket router (`/ws`) with `subscribe`/`unsubscribe` actions.
- Watchlist CRUD (`routers/watchlist.py` + `models/watchlist.py`).
- Profile + candles routers (for Charts page).
- Heatmap service + router.
- Alerts: `models/alert.py`, `AlertEngine` (tick-driven evaluation, rehydrates from DB on startup), `routers/alerts.py`, `AlertForm.tsx`.
- Debug tick injection endpoint (`POST /api/debug/tick`, gated by `DEBUG`).
- Frontend shell: React Router layout in `App.tsx`, Tailwind styling, nav sidebar.
- Frontend pages wired up: Watchlist, Charts, Heatmap, Alerts.

**Phase 6 — Paper Trading (backend done, frontend pending)**
- Backend complete: `services/paper_trading.py` (Decimal-based buy/sell with weighted-avg cost, portfolio view with live PnL), `models/paper.py`, `routers/paper.py`, and `backend/tests/test_paper.py`.
- Frontend: `frontend/src/pages/PaperTradingPage.tsx` is still a stub — **"Portfolio lands in Phase 6."** Needs a real UI: portfolio summary (cash / market value / total / PnL), positions table, buy/sell form wired to `/api/paper/*`.

**Phase 7 — News + sentiment (not started)**
- `vaderSentiment` is in `requirements.txt` but there is no news router/service yet.
- `frontend/src/pages/NewsPage.tsx` is a stub — **"News + sentiment lands in Phase 7."**
- Routes `/news` and `/news/:symbol` already exist in `App.tsx`, so the frontend just needs real content.
- Likely next steps: pick a news source (Finnhub has `/company-news`), add `services/news.py` + `routers/news.py`, run headlines through VADER, render in `NewsPage`.

**Housekeeping gaps**
- **No git repo** — `.gitignore` exists but `.git/` does not. `git init` + initial commit before continuing is a good idea.
- **No Alembic migrations** — `backend/alembic/versions/` is empty. Schema is currently created via `init_models()` (likely `Base.metadata.create_all`). Before any schema change, generate a baseline migration.
- **Thin test coverage** — only `backend/tests/test_paper.py`. Consider adding tests for `AlertEngine` and the watchlist router next.
- **Unusual version pins** — `frontend/package.json` has `typescript ~6.0.2` and `vite ^8.0.4`; verify they still resolve when reinstalling `node_modules` on a new machine.
- `.env` is gitignored and must be created locally with at least `FINNHUB_API_KEY=...`.

**Suggested next session starting point**
1. `git init` and commit current state.
2. Build out `PaperTradingPage.tsx` against the existing `/api/paper` endpoints (backend + tests already in place, so this should be pure frontend work).
3. Then start Phase 7 (news + sentiment) from the backend side.
