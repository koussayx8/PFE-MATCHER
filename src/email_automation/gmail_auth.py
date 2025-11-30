import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config.settings import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_SCOPES

logger = logging.getLogger(__name__)

def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2.
    
    Returns:
        Resource: Gmail API service object or None if failed.
    """
    creds = None
    
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(GMAIL_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)
        except Exception as e:
            logger.warning(f"Invalid token file: {e}")
            
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired token...")
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
                
        if not creds:
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                logger.error(f"credentials.json not found at {GMAIL_CREDENTIALS_PATH}")
                return None
                
            try:
                logger.info("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(GMAIL_CREDENTIALS_PATH), GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                return None
                
        # Save the credentials for the next run
        try:
            with open(GMAIL_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            logger.warning(f"Failed to save token: {e}")

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return None
