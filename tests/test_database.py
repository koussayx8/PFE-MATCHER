import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data_management.models import Base, Application, Match
from src.data_management.database import save_match_batch, log_application, get_statistics

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

def test_save_match_batch(db_session):
    matches = [
        {
            "project_id": "1",
            "project_title": "Test Project",
            "company": "Test Corp",
            "overall_score": 85,
            "recommendation": "Apply",
            "matching_points": ["Good fit"],
            "gaps": ["None"]
        }
    ]
    
    save_match_batch(matches)
    
    saved = db_session.query(Match).first()
    assert saved.project_title == "Test Project"
    assert saved.score == 85

def test_log_application(db_session):
    project = {"id": "1", "title": "Test Project", "company": "Test Corp"}
    match_data = {"overall_score": 90}
    email_data = {"subject": "Hi", "body": "Hello"}
    
    app_id = log_application(project, match_data, email_data)
    
    assert app_id is not None
    saved = db_session.query(Application).first()
    assert saved.status == "pending"
    assert saved.match_score == 90

def test_get_statistics(db_session):
    # Add some data
    app1 = Application(status="sent", match_score=80)
    app2 = Application(status="responded", match_score=90)
    db_session.add_all([app1, app2])
    db_session.commit()
    
    stats = get_statistics()
    
    assert stats["total_applications"] == 2
    assert stats["sent_emails"] == 1
    assert stats["responses"] == 1
    assert stats["avg_match_score"] == 85.0
