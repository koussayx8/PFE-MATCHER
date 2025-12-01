import unittest
from src.ai_engine.project_extractor import normalize_projects

class TestGlobalLinkPropagation(unittest.TestCase):

    def test_propagation(self):
        projects = [
            {
                "title": "Frontend Development Internship",
                "description": "Description A",
                "application_link": "", # Missing
                "application_method": "email"
            },
            {
                "title": "Backend API Engineering",
                "description": "Description B",
                "application_link": "https://stages.mobelite.fr", # Found
                "application_method": "link"
            },
            {
                "title": "Data Science Research",
                "description": "Description C",
                "application_link": "", # Missing
                "application_method": "email"
            }
        ]
        
        cleaned = normalize_projects(projects)
        
        # Check Project A
        self.assertEqual(cleaned[0]["application_link"], "https://stages.mobelite.fr")
        self.assertEqual(cleaned[0]["application_method"], "link")
        self.assertEqual(cleaned[0].get("_note"), "Inferred from global context")
        
        # Check Project B (Source)
        self.assertEqual(cleaned[1]["application_link"], "https://stages.mobelite.fr")
        
        # Check Project C
        self.assertEqual(cleaned[2]["application_link"], "https://stages.mobelite.fr")

if __name__ == '__main__':
    unittest.main()
