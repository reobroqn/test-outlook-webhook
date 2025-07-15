from fastapi import APIRouter, Request, HTTPException
from loguru import logger
from app.msgraph import create_subscription

router = APIRouter()

@router.post("", status_code=201)
async def create_outlook_subscription(request: Request):
    """
    Endpoint to create or renew the Outlook webhook subscription
    
    Returns:
        JSON response with subscription details or error message
    """
    # Generate the webhook URL using the current request's base URL
    webhook_url = str(request.url_for("outlook_notify"))
    logger.info(f"🔗 Attempting to create subscription with URL: {webhook_url}")
    
    # Create the subscription and get the result
    result = create_subscription(webhook_url=webhook_url)
    
    if result.get("success"):
        return {
            "status": "success",
            "webhook_url": webhook_url,
            "message": result["message"],
            "subscription": result.get("data", {})
        }
    else:
        error_msg = result.get("error", "Unknown error occurred")
        logger.error(f"❌ {error_msg}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": result.get("message", "Failed to create subscription"),
                "error": error_msg
            }
        )
