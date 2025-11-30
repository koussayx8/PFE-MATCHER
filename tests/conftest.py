import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

@pytest.fixture
def sample_cv_text():
    return """
    John Doe
    Software Engineer
    Skills: Python, React, Docker
    Experience: 
    - Developer at Tech Corp (2020-2023)
    """

@pytest.fixture
def sample_project_text():
    return """
    Project Title: AI Chatbot
    Description: Build a chatbot using NLP.
    Technologies: Python, TensorFlow
    Company: AI Solutions
    Email: contact@aisolutions.com
    """
