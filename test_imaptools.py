from __future__ import annotations
import os
import sys
import time
import socket
import imaplib
import ssl
import traceback
from typing import List, Optional, Tuple, Type, TypeVar
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from imap_tools import MailBox, AND, A, MailboxLoginError, MailboxLogoutError, MailMessage

# Type aliases
Seconds = float
ExceptionType = Type[BaseException]


class IMAPIdleClient:
    """IMAP IDLE client with reconnection support and type hints."""
    def __init__(self) -> None:
        """Initialize the IMAP IDLE client with configuration from environment variables."""
        load_dotenv()
        
        # Configuration with type hints
        self.imap_server: str = os.getenv('IMAP_SERVER', 'imap.tma.com.vn')
        self.username: Optional[str] = os.getenv('EMAIL_USERNAME')
        self.password: Optional[str] = os.getenv('EMAIL_PASSWORD')
        self.folder: str = os.getenv('EMAIL_FOLDER', 'INBOX')
        self.ssl_context: ssl.SSLContext = ssl.create_default_context()
        
        # Disable SSL verification (use only for testing with self-signed certificates)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        if not all([self.username, self.password]):
            raise ValueError("Please set EMAIL_USERNAME and EMAIL_PASSWORD in .env file")
    
    def process_message(self, msg: MailMessage) -> None:
        """Process a new email message.
        
        Args:
            msg: The email message to process
        """
        try:
            logger.info("\n" + "="*60)
            logger.info(f"NEW EMAIL RECEIVED - {datetime.now()}")
            logger.info("="*60)
            
            # Basic email information
            logger.info(f"From: {msg.from_}")
            logger.info(f"To: {msg.to}")
            logger.info(f"Date: {msg.date}")
            logger.info(f"Subject: {msg.subject}")
            
            # Print text content
            if msg.text:
                logger.info("\n--- MESSAGE BODY ---")
                logger.info(msg.text.strip())
            
            # Print HTML content if no text content
            elif msg.html:
                logger.info("\n--- HTML CONTENT (first 500 chars) ---")
                logger.info(msg.html[:500] + (msg.html[500:] and '...'))
            
            # Print attachments info
            if msg.attachments:
                logger.info("\n--- ATTACHMENTS ---")
                for att in msg.attachments:
                    logger.info(f"- {att.filename} ({len(att.payload)} bytes)")
            
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.debug(traceback.format_exc())
    
    def idle_callback(self, mailbox: MailBox) -> None:
        """Process new messages in IDLE mode.
        
        Args:
            mailbox: The connected mailbox instance
            
        Raises:
            Exception: If there's an error processing messages
        """
        try:
            for msg in mailbox.fetch(AND(seen=False), mark_seen=True):
                self.process_message(msg)
        except Exception as e:
            logger.error(f"Error in idle callback: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    def _handle_initial_connection(self, mailbox: MailBox) -> None:
        """Handle initial connection setup and authentication.
        
        Args:
            mailbox: The connected mailbox instance
            
        Raises:
            MailboxLoginError: If authentication fails
        """
        if not self.username or not self.password:
            raise ValueError("Username and password must be set")
            
        logger.info("Authenticating...")
        mailbox.login(self.username, self.password, self.folder)
        logger.info(f"Successfully logged in to {self.folder}")
        
        # Get initial message count
        try:
            messages = list(mailbox.fetch(AND(seen=False)))
            logger.info(f"Found {len(messages)} unread messages")
        except Exception as e:
            logger.warning(f"Could not fetch initial messages: {e}")
    
    def _run_idle_loop(self, mailbox: MailBox) -> None:
        """Run the IDLE loop to listen for new messages.
        
        Args:
            mailbox: The connected mailbox instance
            
        Raises:
            KeyboardInterrupt: When user interrupts the process
            ConnectionError: When connection is lost
        """
        logger.info("\nStarting IDLE mode. Press Ctrl+C to exit...")
        logger.info("Waiting for new emails...")
        
        try:
            while True:
                try:
                    # Wait for notifications with a timeout
                    responses = mailbox.idle.wait(timeout=45)  # 3 minutes
                    logger.debug(f"IDLE responses: {responses}")
                    
                    if responses:
                        self.idle_callback(mailbox)
                    else:
                        logger.info("No new emails in the last 45 seconds")
                    
                except (ConnectionError, imaplib.IMAP4.abort) as e:
                    logger.error(f"Connection error: {e}")
                    logger.debug(traceback.format_exc())
                    raise ConnectionError("Connection lost") from e
                    
                except Exception as e:
                    logger.error(f"Unexpected error in IDLE loop: {e}")
                    logger.debug(traceback.format_exc())
                    time.sleep(1)  # Prevent tight loop on errors
        
        except KeyboardInterrupt:
            logger.info("\nExiting IDLE mode...")
        except Exception as e:
            logger.error(f"Error in IDLE loop: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    def idle_callback(self, mailbox: MailBox) -> None:
        """Process new messages in IDLE mode.
        
        Args:
            mailbox: The connected mailbox instance
        """
        try:
            # Fetch only unseen messages
            for msg in mailbox.fetch(A(seen=False), mark_seen=True):
                self.process_message(msg)
        except Exception as e:
            logger.error(f"Error in idle callback: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    def run(self) -> None:
        """Run the IMAP IDLE client with reconnection support.
        
        This is the main loop that handles connection, reconnection, and error handling.
        Based on the reliable console notifier example from imap-tools documentation.
        """
        done = False
        
        while not done:
            connection_start_time = time.monotonic()
            connection_live_time = 0.0
            
            try:
                logger.info(f"Connecting to {self.imap_server}...")
                
                with MailBox(self.imap_server) as mailbox:
                    print(mailbox.client.capability(), mailbox.client.capabilities)
                    try:
                        # Handle initial connection and authentication
                        self._handle_initial_connection(mailbox)
                        logger.info("Connection established")
                        
                        # Main IDLE loop
                        while connection_live_time < 29 * 60:  # Reconnect every 29 minutes
                            try:
                                # Run IDLE with a 3-minute timeout
                                self._run_idle_loop(mailbox)
                                
                            except KeyboardInterrupt:
                                logger.info("Shutdown requested by user")
                                done = True
                                break
                                
                            except Exception as e:
                                logger.error(f"Error in IDLE loop: {e}")
                                logger.debug(traceback.format_exc())
                                break  # Will trigger reconnection
                            
                            connection_live_time = time.monotonic() - connection_start_time
                        
                        if done:
                            break
                            
                    except (MailboxLoginError, MailboxLogoutError) as e:
                        logger.error(f"Authentication error: {e}")
                        logger.debug(traceback.format_exc())
                        time.sleep(60)  # Wait before retrying
                    
            except (TimeoutError, ConnectionError, 
                   imaplib.IMAP4.abort, socket.herror, 
                   socket.gaierror, socket.timeout) as e:
                logger.error(f"Connection error: {e}")
                logger.debug(traceback.format_exc())
                logger.info("Reconnecting in 60 seconds...")
                time.sleep(60)
                
            except Exception as e:
                logger.critical(f"Unexpected error: {e}")
                logger.debug(traceback.format_exc())
                logger.info("Reconnecting in 60 seconds...")
                time.sleep(60)
        
        logger.info("IMAP client stopped")

def main() -> None:
    """Main entry point for the IMAP IDLE client."""
    try:
        client = IMAPIdleClient()
        client.run()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        return 1  # Non-zero exit code on error
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)
