from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger
from app.routers import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Log that the application is starting
    logger.info("🚀 Application starting up...")
    logger.info("POST to /api/subscriptions to create a webhook subscription")
    
    yield  # Application runs here
    
    # Shutdown: Add any cleanup code here if needed
    logger.info("👋 Application shutting down")

app = FastAPI(lifespan=lifespan)

# Include all API routes from the routers package
app.include_router(api_router)
