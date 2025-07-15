import os
import datetime
import requests
from loguru import logger
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# -----------------------------------------------------------------------------
# Configuration – values are expected in environment variables for security.
# -----------------------------------------------------------------------------
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
# The user (or shared mailbox) to monitor. Use user principal name or id.
USER_ID = os.getenv("AZURE_USER_ID")

if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, USER_ID]):
    logger.warning(
        "Azure credentials (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, "
        "AZURE_TENANT_ID, AZURE_USER_ID) are not fully set. "
        "MS Graph subscription will not be created."
    )

# Scopes for application-permission token
GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]

# -----------------------------------------------------------------------------
# Authentication helpers
# -----------------------------------------------------------------------------

def get_token() -> str:
    """Acquire an app-only (client credentials) access token using MSAL."""
    app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_silent(GRAPH_SCOPES, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPES)

    if "access_token" not in result:
        error = result.get("error_description")
        logger.error(f"Failed to obtain access token: {error}")
        raise RuntimeError(error or "Unknown error acquiring token")

    return result["access_token"]

# -----------------------------------------------------------------------------
# Subscription helpers
# -----------------------------------------------------------------------------

def create_subscription(webhook_url: str) -> dict:
    """Create or renew a Microsoft Graph subscription for new e-mails.
    
    Args:
        webhook_url: The full URL where Microsoft Graph will send notifications
        
    Returns:
        dict: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Status message
            - data (dict, optional): Response data on success
            - error (str, optional): Error message on failure
    """
    if not all([CLIENT_ID, CLIENT_SECRET, TENANT_ID, USER_ID]):
        error_msg = "Missing Azure credentials - cannot create subscription"
        logger.warning(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "error": "Missing required Azure credentials"
        }

    try:
        token = get_token()
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
            "resource": f"/users/{USER_ID}/mailFolders('Inbox')/messages",
            "expirationDateTime": expiration,
            "clientState": "verify-me",
        }

        resp = requests.post(
            "https://graph.microsoft.com/v1.0/subscriptions", 
            headers=headers, 
            json=body,
            timeout=30  # Add timeout to prevent hanging
        )
        
        resp.raise_for_status()  # Will raise HTTPError for 4XX/5XX responses
        
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
