import asyncio
import os
from dotenv import load_dotenv
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from loguru import logger

# Load environment variables
load_dotenv()

# Configuration
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
USER_ID = os.getenv("AZURE_USER_ID")  # User Principal Name or ID to look up

async def get_user():
    """Get user details from Microsoft Graph"""
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, USER_ID]):
        missing = []
        if not TENANT_ID: missing.append("AZURE_TENANT_ID")
        if not CLIENT_ID: missing.append("AZURE_CLIENT_ID")
        if not CLIENT_SECRET: missing.append("AZURE_CLIENT_SECRET")
        if not USER_ID: missing.append("AZURE_USER_ID")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    # Initialize credentials
    credential = None
    client = None
    
    try:
        # Initialize credentials and client
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        
        scopes = ['https://graph.microsoft.com/.default']

        logger.info("This is token: " + (await credential.get_token(scopes[0])).token)
        client = GraphServiceClient(credentials=credential, scopes=scopes)
        
        logger.info(f"Tenant ID: {TENANT_ID}")
        logger.info(f"Client ID: {CLIENT_ID}")
        logger.info(f"User ID: {USER_ID}")
        logger.info(f"Fetching user details for: {USER_ID}")
        
        # Get user details
        user = await client.users.by_user_id(USER_ID).get()
        
        if user:
            logger.success("✅ Successfully retrieved user details")
            print("\nUser Details:")
            print(f"Display Name: {user.display_name}")
            print(f"User Principal Name: {user.user_principal_name}")
            print(f"ID: {user.id}")
            print(f"Mail: {getattr(user, 'mail', 'N/A')}")
            print(f"Job Title: {getattr(user, 'job_title', 'N/A')}")
            return user
        else:
            logger.warning("No user found with the provided ID/UPN")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error fetching user details: {str(e)}")
        # Print more detailed error information
        logger.debug(f"Error type: {type(e).__name__}")
        if hasattr(e, 'status_code'):
            logger.debug(f"Status code: {e.status_code}")
        if hasattr(e, 'message'):
            logger.debug(f"Error message: {e.message}")
        # Log additional error details if available
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.debug(f"Response: {e.response.text}")
        raise
        
    finally:
        # Clean up resources
        if credential:
            await credential.close()
        if client and hasattr(client, 'close'):
            await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(get_user())
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        exit(1)
