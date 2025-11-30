import pytest
from src.document_processing.validators import validate_email, extract_emails_from_text
from src.document_processing.text_cleaner import clean_text

def test_validate_email():
    assert validate_email("test@example.com")[0] == True
    assert validate_email("invalid-email")[0] == False
    
def test_extract_emails():
    text = "Contact us at info@test.com or support@test.com"
    emails = extract_emails_from_text(text)
    assert "info@test.com" in emails
    assert "support@test.com" in emails
    assert len(emails) == 2

def test_clean_text():
    raw = "Hello   World\n\n\nTest"
    cleaned = clean_text(raw)
    assert cleaned == "Hello World\n\nTest"
