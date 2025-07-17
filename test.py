import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.subscription import Subscription
from loguru import logger

# Load environment variables
load_dotenv()

# Configuration
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
USER_ID = os.getenv("AZURE_USER_ID")
SCOPES = ["https://graph.microsoft.com/.default"]

# Webhook configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
print("This is webhook url: ", WEBHOOK_URL)

class GraphTester:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.tenant_id = TENANT_ID
        self.user_id = USER_ID
        self.scopes = SCOPES
        self._validate_credentials()
        self.graph_client = self._get_graph_client()
    
    def _validate_credentials(self):
        """Validate that all required credentials are present"""
        if not all([self.client_id, self.client_secret, self.tenant_id, self.user_id]):
            raise ValueError("Missing required Azure AD credentials")
        logger.debug("✅ All required credentials are present")
    
    def _get_graph_client(self):
        """Initialize and return a Graph client with client credentials"""
        logger.debug("Initializing Graph client")
        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        return GraphServiceClient(credential, scopes=["https://graph.microsoft.com/.default"])
    
    async def create_subscription(self, webhook_url: str) -> dict:
        """
        Create a new subscription using Microsoft Graph SDK
        
        Args:
            webhook_url: The HTTPS URL for receiving change notifications
            
        Returns:
            dict: Subscription details or error information
        """
        try:
            # Calculate expiration (max 3 days for message subscriptions)
            expiration = datetime.now(timezone.utc) + timedelta(minutes=4230)  # ~3 days - 30 minutes
            
            subscription = Subscription(
                change_type="created,updated",
                notification_url=webhook_url,
                resource=f"users/{self.user_id}/mailFolders('Inbox')/messages",
                expiration_date_time=expiration,
                client_state="test-subscription-123"
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
            return {
                "success": False,
                "message": "Failed to create subscription",
                "error": error_msg
            }

async def main():
    """Main function to test Microsoft Graph webhook subscription"""
    # Validate environment variables
    required_vars = {
        "AZURE_CLIENT_ID": CLIENT_ID,
        "AZURE_CLIENT_SECRET": CLIENT_SECRET,
        "AZURE_TENANT_ID": TENANT_ID,
        "AZURE_USER_ID": USER_ID,
        "WEBHOOK_URL": WEBHOOK_URL
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"- {var}")
        logger.error("\nPlease check your .env file.")
        return
    
    if not WEBHOOK_URL.startswith('https://'):
        logger.error("WEBHOOK_URL must use HTTPS")
        logger.error("Microsoft Graph requires HTTPS for webhook endpoints")
        return
    
    logger.info("🚀 Starting Microsoft Graph Webhook Test")
    logger.info(f"Tenant ID: {TENANT_ID}")
    logger.info(f"Client ID: {CLIENT_ID}")
    logger.info(f"User ID: {USER_ID}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    try:
        tester = GraphTester()
        result = await tester.create_subscription(WEBHOOK_URL)
        
        if not result.get('success'):
            logger.error("Failed to create subscription")
            if 'error' in result:
                logger.error(f"Error: {result['error']}")
        else:
            logger.success("✅ Test completed successfully!")
        
        return result
        
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        logger.exception("Full error details:")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
