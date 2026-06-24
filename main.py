from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import Base, engine
from app.core.config import settings
from app.core.ws_manager import ws_manager
from app.api import auth, stock, integrations, factures, alertes, dashboard
from app.license_client import verifier_licence_au_demarrage

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    is_valid = await verifier_licence_au_demarrage()
    if not is_valid:
        raise RuntimeError("Licence invalide — demarrage refuse")
    yield


app = FastAPI(
    title="Synexia Tenant Server",
    version="2.0.0",
    description="Serveur local Synexia — Smart Warehouse",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1/auth",         tags=["Auth"])
app.include_router(stock.router,        prefix="/api/v1/stock",        tags=["Stock"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations IA/IoT"])
app.include_router(factures.router,     prefix="/api/v1/factures",     tags=["Factures"])
app.include_router(alertes.router,      prefix="/api/v1/alertes",      tags=["Alertes"])
app.include_router(dashboard.router,    prefix="/api/v1/dashboard",    tags=["Dashboard"])


@app.get("/", tags=["Sante"])
def root():
    return {"status": "running", "service": "Synexia Tenant Server", "version": "2.0.0"}


@app.get("/health", tags=["Sante"])
def health():
    return {"status": "ok"}


@app.websocket("/ws/alertes")
async def websocket_alertes(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
