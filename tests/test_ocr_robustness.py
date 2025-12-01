import unittest
import re

class TestOCRRobustness(unittest.TestCase):
    
    def setUp(self):
        # Regex patterns to test (will be moved to project_extractor.py)
        self.url_pattern = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+|bit\.ly/[^\s<>"]+|forms\.gle/[^\s<>"]+)', re.IGNORECASE)
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    def clean_ocr_email(self, text):
        # Placeholder for the logic I plan to implement
        text = text.replace("(ö", "@").replace("(at)", "@").replace("[at]", "@")
        return text

    def clean_ocr_url(self, text):
        # Placeholder for URL cleaning
        # Fix common OCR typos in standard protocols
        text = text.replace("https://staqes", "https://stages")
        return text

    def test_mobelite_link_typo(self):
        text = "Pour postuler il faut se connecter å : https://staqes.mobelite.fr remplir le formulaire"
        
        # 1. Test raw extraction (might fail or get the typo)
        match = self.url_pattern.search(text)
        extracted = match.group(0) if match else None
        
        # 2. Test cleaning
        if extracted:
            cleaned = self.clean_ocr_url(extracted)
            self.assertEqual(cleaned, "https://stages.mobelite.fr")
        else:
            self.fail("Could not extract link from text")

    def test_capgemini_email_typo(self):
        text = "Email stagetunisie.tn(öcapgemini.com Suivez nos actualités"
        
        # 1. Pre-clean text
        cleaned_text = self.clean_ocr_email(text)
        
        # 2. Extract
        match = self.email_pattern.search(cleaned_text)
        extracted = match.group(0) if match else None
        
        self.assertEqual(extracted, "stagetunisie.tn@capgemini.com")

if __name__ == '__main__':
    unittest.main()
