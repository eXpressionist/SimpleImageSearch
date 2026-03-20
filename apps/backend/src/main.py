import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import batches_router, items_router, images_router, health_router
from src.infrastructure.database import engine
from src.infrastructure.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    
    async with engine.begin() as conn:
        from src.infrastructure.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created")
    
    yield
    
    logger.info("Shutting down...")


app = FastAPI(
    title="Simple Image Search API",
    description="Batch image search and download via Google Custom Search",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(batches_router, prefix="/api")
app.include_router(items_router, prefix="/api")
app.include_router(images_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Simple Image Search API", "docs": "/docs"}
