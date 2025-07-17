import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.subscription import Subscription
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
        self.graph_client = self._get_graph_client()
    
    def _validate_credentials(self):
        """Validate that all required credentials are present"""
        missing = []
        if not self.client_id: missing.append("AZURE_CLIENT_ID")
        if not self.client_secret: missing.append("AZURE_CLIENT_SECRET")
        if not self.tenant_id: missing.append("AZURE_TENANT_ID")
        if not self.user_id: missing.append("AZURE_USER_ID")
        
        if missing:
            error_msg = f"Missing required Azure AD credentials: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug("✅ All required credentials are present")
    
    def _get_graph_client(self) -> GraphServiceClient:
        """Initialize and return a Graph client with client credentials"""
        logger.debug("Initializing Graph client")
        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        return GraphServiceClient(credential, scopes=self.scopes)
    
    async def create_subscription(self, webhook_url: str) -> Dict[str, Any]:
        """
        Create or renew a Microsoft Graph subscription for new e-mails.
        
        Args:
            webhook_url: The HTTPS URL where Microsoft Graph will send notifications
            
        Returns:
            dict: A dictionary containing status and response data
        """
        try:
            # Calculate expiration (max 3 days for message subscriptions)
            expiration = datetime.now(timezone.utc) + timedelta(minutes=4230)  # ~3 days - 30 minutes
            
            subscription = Subscription(
                change_type="created,updated",
                notification_url=webhook_url,
                resource=f"users/{self.user_id}/mailFolders('Inbox')/messages",
                expiration_date_time=expiration,
                client_state="verify-me"
            )
            
            logger.info(f"Creating subscription with webhook URL: {webhook_url}")
            logger.info(f"Subscription will expire at: {expiration.isoformat()}")
            
            # Create subscription using Graph SDK
            result = await self.graph_client.subscriptions.post(subscription)
            
            logger.success("✅ Subscription created successfully!")
            logger.debug(f"Subscription details: {result}")
            
            return {
                "success": True,
                "message": "Subscription created successfully",
                "data": result
            }
            
        except Exception as e:
            error_msg = f"Failed to create subscription: {str(e)}"
            logger.error(error_msg)
            
            # Add more detailed error information if available
            error_details = {"type": type(e).__name__, "message": str(e)}
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details["response"] = e.response.text
            
            logger.debug(f"Error details: {error_details}")
            
            return {
                "success": False,
                "message": "Failed to create subscription",
                "error": error_msg,
                "error_details": error_details
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
    try:
        # Generate the webhook URL using the current request's base URL
        if os.getenv("WEBHOOK_URL"):
            webhook_url = os.getenv("WEBHOOK_URL")
        else:
            # Ensure HTTPS is used for the webhook URL
            webhook_url = str(request.url_for("outlook_notify")).replace('http://', 'https://')
        
        logger.info(f"🔗 Attempting to create subscription with URL: {webhook_url}")
        
        if not webhook_url.startswith('https://'):
            error_msg = "WEBHOOK_URL must use HTTPS"
            logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "message": error_msg,
                    "error": "Microsoft Graph requires HTTPS for webhook endpoints"
                }
            )
        
        # Create the subscription and get the result
        result = await graph_client.create_subscription(webhook_url=webhook_url)
        
        if result.get("success"):
            return {
                "status": "success",
                "webhook_url": webhook_url,
                "message": result["message"],
                "subscription": result.get("data", {})
            }
        else:
            error_msg = result.get("error", "Unknown error occurred")
            error_details = result.get("error_details", {})
            logger.error(f"❌ {error_msg}")
            
            status_code = 500
            if "Unauthorized" in error_msg or "AuthenticationFailed" in error_msg:
                status_code = 401
            elif "NotFound" in error_msg:
                status_code = 404
                
            raise HTTPException(
                status_code=status_code,
                detail={
                    "status": "error",
                    "message": result.get("message", "Failed to create subscription"),
                    "error": error_msg,
                    "error_details": error_details
                }
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in create_outlook_subscription: {str(e)}")
        logger.exception("Full error details:")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred",
                "error": str(e)
            }
        )
