import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def send_email(service, to_email: str, subject: str, body: str, from_email: str = "me") -> Dict[str, Any]:
    """
    Send an email using the Gmail API.
    
    Args:
        service: Authenticated Gmail service.
        to_email: Recipient email.
        subject: Email subject.
        body: Email body (HTML supported).
        from_email: Sender email (default 'me').
        
    Returns:
        Dict: Result status.
    """
    if not service:
        return {"success": False, "error": "Gmail service not authenticated"}

    try:
        message = MIMEMultipart()
        message['to'] = to_email
        message['from'] = from_email
        message['subject'] = subject
        
        msg = MIMEText(body, 'html')
        message.attach(msg)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        body = {'raw': raw_message}
        
        logger.info(f"Sending email to {to_email}...")
        sent_message = service.users().messages().send(userId=from_email, body=body).execute()
        
        logger.info(f"Email sent! Message Id: {sent_message['id']}")
        return {
            "success": True, 
            "message_id": sent_message['id'], 
            "thread_id": sent_message['threadId']
        }
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return {"success": False, "error": str(e)}
