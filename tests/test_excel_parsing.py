import unittest
import pandas as pd
from src.document_processing.excel_parser import parse_excel_to_projects
import os

class TestExcelParsing(unittest.TestCase):
    
    def setUp(self):
        self.test_file = "test_projects.xlsx"
        # Create a dummy Excel file with the user's columns
        data = {
            "Stage": ["Project Alpha", "Project Beta"],
            "Société": ["Company A", "Company B"],
            "Description": ["Desc A", "Desc B"],
            "Lien": ["http://a.com", "http://b.com"]
        }
        df = pd.DataFrame(data)
        df.to_excel(self.test_file, index=False)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_parsing(self):
        projects = parse_excel_to_projects(self.test_file)
        
        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["title"], "Project Alpha")
        self.assertEqual(projects[0]["company"], "Company A")
        self.assertEqual(projects[0]["application_link"], "http://a.com")

if __name__ == '__main__':
    unittest.main()
