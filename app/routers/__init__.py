"""
Routers package for the FastAPI application.

This module collects and exports all route definitions from individual router modules.
"""
from fastapi import APIRouter
from . import example, outlook_webhook, subscription

# Create a main router to include all other routers
router = APIRouter()
router.include_router(example.router, tags=["example"])
router.include_router(outlook_webhook.router, tags=["webhooks"])
router.include_router(
    subscription.router,
    prefix="/api/subscriptions",
    tags=["subscriptions"]
)

# Export all routers for easy access
__all__ = ["router"]
