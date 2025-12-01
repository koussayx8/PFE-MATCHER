import unittest
from unittest.mock import patch, MagicMock
import json
from src.ai_engine.perplexity_enricher import chat_completion, research_company
from src.ai_engine.matcher import match_project_to_cv

class TestPerplexityIntegration(unittest.TestCase):

    @patch('src.ai_engine.perplexity_enricher.requests.post')
    def test_chat_completion_success(self, mock_post):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"test": "success"}'}}]
        }
        mock_post.return_value = mock_response
        
        result = chat_completion([{"role": "user", "content": "test"}])
        self.assertEqual(result, '{"test": "success"}')

    @patch('src.ai_engine.perplexity_enricher.requests.post')
    def test_research_company_success(self, mock_post):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': '{"description": "A company", "recent_news": [], "values": []}'}}]
        }
        mock_post.return_value = mock_response
        
        with patch('src.ai_engine.perplexity_enricher.PERPLEXITY_API_KEY', 'fake_key'):
            result = research_company("Test Corp")
            self.assertEqual(result.get("description"), "A company")

    @patch('src.ai_engine.matcher.GeminiClient')
    @patch('src.ai_engine.perplexity_enricher.chat_completion')
    def test_matcher_fallback(self, mock_perplexity, mock_gemini_cls):
        # Mock Gemini failure
        mock_gemini_instance = mock_gemini_cls.return_value
        mock_gemini_instance.generate_structured_response.side_effect = Exception("Quota Exceeded")
        
        # Mock Perplexity success
        mock_perplexity.return_value = json.dumps({
            "overall_score": 85,
            "matching_points": ["Point 1"],
            "gaps": [],
            "recommendation": "Strong Match"
        })
        
        cv_data = {"skills": "Python"}
        project = {"id": "1", "title": "Dev", "company": "Corp"}
        
        # Run match
        result = match_project_to_cv(cv_data, project, cv_hash="hash")
        
        # Verify fallback was used
        self.assertEqual(result["overall_score"], 85)
        self.assertEqual(result["source"], "perplexity")
        mock_perplexity.assert_called_once()

if __name__ == '__main__':
    unittest.main()
