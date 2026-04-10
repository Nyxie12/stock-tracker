import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import SessionLocal, init_models
from .routers import alerts, candles, debug, heatmap, news, paper, profile, quote, watchlist, ws
from .services.alert_engine import AlertEngine
from .services.connection_manager import ConnectionManager
from .services.finnhub_client import FinnhubClient
from .services.finnhub_stream import FinnhubStream
from .services.heatmap import HeatmapService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()

    stream = FinnhubStream(api_key=settings.finnhub_api_key, throttle_ms=settings.tick_throttle_ms)
    finnhub = FinnhubClient(api_key=settings.finnhub_api_key)
    manager = ConnectionManager(stream=stream)

    alert_engine = AlertEngine(session_factory=SessionLocal, stream=stream, manager=manager)

    async def _on_tick(symbol: str, price: float, ts: int) -> None:
        await alert_engine.on_tick(symbol, price, ts)
        await manager.broadcast_tick(symbol, price, ts)

    stream.add_subscriber(_on_tick)
    await stream.start()
    await alert_engine.load_from_db()

    app.state.stream = stream
    app.state.finnhub = finnhub
    app.state.manager = manager
    app.state.alert_engine = alert_engine
    app.state.heatmap = HeatmapService(finnhub=finnhub)

    log.info("stock-tracker started (debug=%s)", settings.debug)
    try:
        yield
    finally:
        await stream.stop()
        await finnhub.close()


app = FastAPI(title="Stock Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(watchlist.router)
app.include_router(profile.router)
app.include_router(quote.router)
app.include_router(candles.router)
app.include_router(heatmap.router)
app.include_router(alerts.router)
app.include_router(paper.router)
app.include_router(news.router)
app.include_router(debug.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
