import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

def test_imports():
    from src.document_processing.pdf_parser import extract_text_from_pdf
    from src.document_processing.excel_parser import parse_excel_to_projects
    from src.document_processing.text_cleaner import clean_text
    from src.document_processing.validators import validate_email
    
    print("Imports successful!")

if __name__ == "__main__":
    test_imports()
