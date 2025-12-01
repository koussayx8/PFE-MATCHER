import unittest
from src.ai_engine.project_extractor import normalize_projects

class TestRegexFallback(unittest.TestCase):

    def test_regex_extraction(self):
        projects = [
            {
                "title": "Test Project",
                "description": "Apply at https://company.com/jobs/123 now.",
                "application_link": "",
                "application_method": "email"
            },
            {
                "title": "No Link Project",
                "description": "Just email us.",
                "application_link": "",
                "application_method": "email"
            }
        ]
        
        cleaned = normalize_projects(projects)
        
        # Project 1 should have link extracted
        self.assertEqual(cleaned[0]["application_link"], "https://company.com/jobs/123")
        self.assertEqual(cleaned[0]["application_method"], "link")
        
        # Project 2 should remain as is
        self.assertEqual(cleaned[1]["application_link"], "")

if __name__ == '__main__':
    unittest.main()
