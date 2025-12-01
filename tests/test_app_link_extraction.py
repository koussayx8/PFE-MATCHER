import unittest
from unittest.mock import patch, MagicMock
import json
from src.ai_engine.project_extractor import extract_projects_from_text
from config.prompts import PROJECT_EXTRACTION_PROMPT

class TestAppLinkExtraction(unittest.TestCase):

    @patch('src.ai_engine.project_extractor.GeminiClient')
    def test_extraction_with_link(self, mock_client_cls):
        # Mock Gemini response
        mock_client = mock_client_cls.return_value
        mock_response = {
            "projects": [
                {
                    "title": "Test Project",
                    "description": "Desc",
                    "company": "Test Corp",
                    "technologies": ["Python"],
                    "domain": "IT",
                    "reference_id": "REF-123",
                    "application_method": "link",
                    "application_link": "https://apply.here",
                    "email": ""
                }
            ]
        }
        mock_client.generate_structured_response.return_value = mock_response
        
        text = "Project: Test Project. Ref: REF-123. Apply at https://apply.here"
        projects = extract_projects_from_text(text)
        
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["reference_id"], "REF-123")
        self.assertEqual(projects[0]["application_link"], "https://apply.here")
        self.assertEqual(projects[0]["application_method"], "link")

if __name__ == '__main__':
    unittest.main()
