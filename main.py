from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import Base, engine
from app.api import auth, stock, integrations
from app.license_client import verifier_licence_au_demarrage

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    verifier_licence_au_demarrage()
    yield

app = FastAPI(title="Synexia Tenant Server", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["stock"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["integrations"])

@app.get("/")
def root():
    return {"status": "Synexia Tenant Server running"}
