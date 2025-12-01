import pytest
import numpy as np
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from unittest.mock import MagicMock, patch
from src.ai_engine.embeddings import EmbeddingEngine
from src.ai_engine.matcher import batch_match_projects, match_project_to_cv
from src.data_management.models import ProjectEmbedding, CVEmbedding, MatchCache, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Patch the session in database module
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.data_management.database.SessionLocal", lambda: session)
        yield session
    
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def mock_sentence_transformer():
    with patch("src.ai_engine.embeddings.SentenceTransformer") as mock:
        model = MagicMock()
        # Mock encode to return random vectors
        model.encode.side_effect = lambda texts: np.random.rand(len(texts), 384) if isinstance(texts, list) else np.random.rand(384)
        mock.return_value = model
        yield mock

def test_embedding_engine_singleton(mock_sentence_transformer):
    e1 = EmbeddingEngine()
    e2 = EmbeddingEngine()
    assert e1 is e2

def test_embed_cv_caching(db_session, mock_sentence_transformer):
    engine = EmbeddingEngine()
    cv_text = "Python Developer with 5 years experience"
    
    # First call - generates
    emb1, hash1 = engine.embed_cv(cv_text)
    assert emb1 is not None
    
    # Verify DB
    cached = db_session.query(CVEmbedding).filter_by(cv_hash=hash1).first()
    assert cached is not None
    
    # Second call - loads from cache (mock shouldn't be called again if we could track it, 
    # but here we check if it returns same object/value)
    emb2, hash2 = engine.embed_cv(cv_text)
    assert hash1 == hash2
    np.testing.assert_array_equal(emb1, emb2)

def test_prefilter_projects(db_session, mock_sentence_transformer):
    engine = EmbeddingEngine()
    cv_text = "Python Data Scientist"
    projects = [
        {"id": "1", "title": "Data Scientist", "description": "Python ML"},
        {"id": "2", "title": "Java Developer", "description": "Spring Boot"},
        {"id": "3", "title": "Frontend", "description": "React JS"}
    ]
    
    # Mock compute_similarities to return predictable scores
    with patch.object(engine, 'compute_similarities') as mock_sim:
        mock_sim.return_value = [("1", 0.9), ("2", 0.2), ("3", 0.1)]
        
        filtered = engine.prefilter_projects(cv_text, projects, top_k=2, min_threshold=0.5)
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

def test_hybrid_matcher_flow(db_session):
    # Mock dependencies
    with patch("src.ai_engine.matcher.EmbeddingEngine") as MockEngine, \
         patch("src.ai_engine.matcher.GeminiClient") as MockGemini:
             
        # Setup Mock Engine
        engine_instance = MockEngine.return_value
        engine_instance.prefilter_projects.return_value = [{"id": "1", "title": "Good Match"}]
        
        # Setup Mock Gemini
        gemini_instance = MockGemini.return_value
        gemini_instance.generate_structured_response.return_value = {"overall_score": 85}
        
        cv_data = {"skills": "Python"}
        projects = [{"id": "1"}, {"id": "2"}]
        
        # Run Matcher
        matches = batch_match_projects(cv_data, projects, min_score=50)
        
        # Verify Pre-filtering called
        engine_instance.prefilter_projects.assert_called_once()
        
        # Verify Gemini called only for filtered result
        assert len(matches) == 1
        assert matches[0]["overall_score"] == 85
        
        # Verify DB Cache
        cached = db_session.query(MatchCache).filter_by(project_id="1").first()
        assert cached is not None
        assert cached.score == 85
