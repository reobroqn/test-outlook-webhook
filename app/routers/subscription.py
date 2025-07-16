import os
import datetime
import requests
from typing import Dict
from msal import ConfidentialClientApplication
from fastapi import APIRouter, Request, HTTPException
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MSGraphClient:
    """Client for interacting with Microsoft Graph API"""
    
    def __init__(self):
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.user_id = os.getenv("AZURE_USER_ID")
        self.scopes = ["https://graph.microsoft.com/.default"]
        
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that all required credentials are present"""
        if not all([self.client_id, self.client_secret, self.tenant_id, self.user_id]):
            raise ValueError("Missing required Azure AD credentials")
    
    def _get_token(self) -> str:
        """Acquire an app-only (client credentials) access token using MSAL"""
        app = ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret,
        )

        result = app.acquire_token_silent(self.scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=self.scopes)

        if "access_token" not in result:
            error = result.get("error_description", "Unknown error acquiring token")
            logger.error(f"Failed to obtain access token: {error}")
            raise HTTPException(status_code=500, detail="Failed to authenticate with Microsoft Graph")

        return result["access_token"]
    
    def create_subscription(self, webhook_url: str) -> Dict:
        """
        Create or renew a Microsoft Graph subscription for new e-mails.
        
        Args:
            webhook_url: The full URL where Microsoft Graph will send notifications
            
        Returns:
            dict: A dictionary containing status and response data
        """
        try:
            token = self._get_token()
            expiration = (
                datetime.datetime.utcnow() + datetime.timedelta(minutes=4200)
            ).isoformat() + "Z"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            body = {
                "changeType": "created",
                "notificationUrl": webhook_url,
                "resource": f"/users/{self.user_id}/mailFolders('Inbox')/messages",
                "expirationDateTime": expiration,
                "clientState": "verify-me",
            }

            resp = requests.post(
                "https://graph.microsoft.com/v1.0/subscriptions",
                headers=headers,
                json=body,
                timeout=60
            )
            
            resp.raise_for_status()
            
            result = resp.json()
            logger.success(f"✅ Subscription created for {webhook_url}")
            return {
                "success": True,
                "message": "Subscription created successfully",
                "data": result
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to create subscription: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_details = e.response.text
                error_msg = f"{error_msg} - {error_details}"
                logger.error(f"❌ {error_msg}")
            
            return {
                "success": False,
                "message": "Failed to create subscription",
                "error": error_msg
            }

# Create router and client instance
router = APIRouter()
graph_client = MSGraphClient()

@router.post("", status_code=201)
async def create_outlook_subscription(request: Request):
    """
    Endpoint to create or renew the Outlook webhook subscription
    
    Returns:
        JSON response with subscription details or error message
    """
    # Generate the webhook URL using the current request's base URL
    if os.getenv("WEBHOOK_URL"):
        webhook_url = os.getenv("WEBHOOK_URL")
    else:
        webhook_url = str(request.url_for("outlook_notify"))
    logger.info(f"🔗 Attempting to create subscription with URL: {webhook_url}")
    
    # Create the subscription and get the result
    result = graph_client.create_subscription(webhook_url=webhook_url)
    
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
