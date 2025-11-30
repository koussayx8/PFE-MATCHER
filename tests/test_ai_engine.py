import pytest
from unittest.mock import MagicMock, patch
from src.ai_engine.cv_analyzer import analyze_cv
from src.ai_engine.matcher import match_project_to_cv

@patch('src.ai_engine.cv_analyzer.GeminiClient')
def test_analyze_cv(mock_client_cls, sample_cv_text):
    mock_client = MagicMock()
    mock_client.generate_structured_response.return_value = {
        "personal_info": {"name": "John Doe"},
        "skills": {"technical": ["Python"]}
    }
    mock_client_cls.return_value = mock_client
    
    result = analyze_cv(sample_cv_text)
    assert result["personal_info"]["name"] == "John Doe"
    assert "Python" in result["skills"]["technical"]

@patch('src.ai_engine.matcher.GeminiClient')
def test_match_project(mock_client_cls):
    mock_client = MagicMock()
    mock_client.generate_structured_response.return_value = {
        "overall_score": 85,
        "recommendation": "Strong Match"
    }
    mock_client_cls.return_value = mock_client
    
    cv = {"skills": ["Python"]}
    project = {"title": "AI Project", "technologies": ["Python"]}
    
    result = match_project_to_cv(cv, project)
    assert result["overall_score"] == 85
    assert result["recommendation"] == "Strong Match"
