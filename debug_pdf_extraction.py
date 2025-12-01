import pdfplumber
from unittest.mock import MagicMock

def test_extraction_logic():
    # Simulate a page with text and annotations
    print("Testing extraction logic...")
    
    # Mock Page
    page = MagicMock()
    page.extract_text.return_value = "Project A: AI System.\nClick here to apply."
    page.annots = [
        {"uri": "https://forms.gle/12345"},
        {"uri": "mailto:hr@mobelite.com"}
    ]
    
    text = ""
    page_text = page.extract_text()
    if page_text:
        text += page_text + "\n"
    
    # Logic from pdf_parser.py
    if page.annots:
        links = []
        for annot in page.annots:
            uri = annot.get("uri")
            if uri:
                links.append(uri)
        
        if links:
            unique_links = list(set(links))
            text += "\n[Extracted Links on Page]:\n" + "\n".join(unique_links) + "\n"
            
    print("--- Extracted Text ---")
    print(text)
    print("----------------------")
    
    if "https://forms.gle/12345" in text:
        print("SUCCESS: Link found in text.")
    else:
        print("FAILURE: Link NOT found in text.")

if __name__ == "__main__":
    test_extraction_logic()
