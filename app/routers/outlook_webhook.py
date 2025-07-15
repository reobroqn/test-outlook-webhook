from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from loguru import logger
import json

router = APIRouter()

@router.post("/outlook-notify", name="outlook_notify")
async def outlook_webhook(request: Request):
    # Step 1: Microsoft validation
    if "validationToken" in request.query_params:
        logger.info("Validation request received from Microsoft Graph.")
        return PlainTextResponse(content=request.query_params["validationToken"], status_code=200)

    # Step 2: Handle notification
    body = await request.json()
    logger.info(f"Received Outlook notification: {json.dumps(body, indent=2)}")
    # Add further processing here as needed
    return {"status": "received"}
