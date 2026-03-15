import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.settings import settings
from src.infrastructure.database.connection import engine
from src.infrastructure.database.models import Base
from src.presentation.api.routes import auth, user, journey
from src.presentation.middleware.security import (
    SecurityHeadersMiddleware,
    LoggingMiddleware,
    setup_cors,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(
    title="AIFSD API",
    description="FastAPI backend for AIFSD App",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(journey.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

