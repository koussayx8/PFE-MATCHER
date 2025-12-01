import unittest
from unittest.mock import patch, MagicMock
from src.document_processing.pdf_parser import extract_text_from_pdf

class TestPDFLinkExtraction(unittest.TestCase):

    @patch('src.document_processing.pdf_parser.pdfplumber.open')
    @patch('src.document_processing.pdf_parser.Path.exists')
    def test_extract_links_from_annotations(self, mock_exists, mock_pdf_open):
        # Setup Mock
        mock_exists.return_value = True
        
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Click here to apply."
        mock_page.annots = [
            {"uri": "https://hidden-link.com/apply"},
            {"uri": "https://another-link.com"}
        ]
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        # Run Extraction
        result = extract_text_from_pdf("dummy.pdf")
        
        # Verify
        text = result["text"]
        self.assertIn("Click here to apply.", text)
        self.assertIn("[Extracted Links on Page]:", text)
        self.assertIn("https://hidden-link.com/apply", text)
        self.assertIn("https://another-link.com", text)

if __name__ == '__main__':
    unittest.main()
