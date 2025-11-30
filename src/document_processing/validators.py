import re
import logging
import dns.resolver
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def validate_email(email: str, check_mx: bool = False) -> Tuple[bool, str]:
    """
    Validate an email address using regex and optional MX record check.
    
    Args:
        email (str): Email address to validate.
        check_mx (bool): Whether to check DNS MX records.
        
    Returns:
        Tuple[bool, str]: (isValid, cleaned_email)
    """
    if not email:
        return False, ""
        
    email = email.strip().lower()
    
    # Basic Regex
    # A more robust regex for emails
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, email
        
    if check_mx:
        try:
            domain = email.split('@')[1]
            dns.resolver.resolve(domain, 'MX')
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception):
            # If DNS check fails, we might still want to accept it if regex passed, 
            # or return False. For now, let's log warning and return True (soft validation)
            # or strict: return False. 
            # Given student context, maybe strict is better to avoid bouncing?
            # But network issues happen. Let's return False only if we are sure it doesn't exist.
            logger.warning(f"MX record check failed for {domain}")
            return False, email

    return True, email

def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract all valid email addresses from a text.
    
    Args:
        text (str): Input text.
        
    Returns:
        List[str]: List of unique valid email addresses.
    """
    if not text:
        return []
        
    # Regex to find emails
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    
    unique_emails = set()
    for email in matches:
        is_valid, cleaned = validate_email(email, check_mx=False)
        if is_valid:
            unique_emails.add(cleaned)
            
    return list(unique_emails)

def validate_project_data(project: Dict[str, Any]) -> bool:
    """
    Validate that a project dictionary has the minimum required fields.
    
    Args:
        project (Dict[str, Any]): Project data.
        
    Returns:
        bool: True if valid.
    """
    required_fields = ["title", "description"]
    
    for field in required_fields:
        if field not in project or not str(project[field]).strip():
            return False
            
    # At least one contact method (email) is highly desirable but maybe not strictly required 
    # if we want to just browse? But for "Auto-Apply", email is critical.
    # Let's say email is required for auto-apply, but maybe not for extraction?
    # The prompt says "Validate minimum required fields".
    # I'll stick to title and description as absolute minimum.
    
    return True
