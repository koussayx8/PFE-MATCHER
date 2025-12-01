import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
import pickle
import numpy as np
from config.settings import DATABASE_URL
from src.data_management.models import Base, Application, Match, ProjectCache, ProjectEmbedding, CVEmbedding, MatchCache

logger = logging.getLogger(__name__)

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    """Dependency to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize the database with required tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def save_match_batch(matches: List[Dict[str, Any]]):
    """Save a batch of matches to the database."""
    session = SessionLocal()
    try:
        for match_data in matches:
            match = Match(
                project_id=match_data.get("project_id"),
                project_title=match_data.get("project_title"),
                company=match_data.get("company"),
                score=match_data.get("overall_score", 0),
                recommendation=match_data.get("recommendation"),
                matching_points=match_data.get("matching_points", []),
                gaps=match_data.get("gaps", []),
                created_at=datetime.now()
            )
            session.add(match)
        session.commit()
        logger.info(f"Saved {len(matches)} matches to database.")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save matches: {e}")
    finally:
        session.close()

def get_recent_matches(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent matches."""
    return get_all_matches(limit=limit)

def get_all_matches(limit: int = None) -> List[Dict[str, Any]]:
    """Retrieve all matches, optionally limited."""
    session = SessionLocal()
    try:
        query = session.query(Match).order_by(Match.created_at.desc())
        if limit:
            query = query.limit(limit)
            
        matches = query.all()
        result = []
        for m in matches:
            match_dict = {
                "project_id": m.project_id,
                "project_title": m.project_title,
                "company": m.company,
                "overall_score": m.score,
                "recommendation": m.recommendation,
                "matching_points": m.matching_points,
                "gaps": m.gaps,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            result.append(match_dict)
        return result
    except Exception as e:
        logger.error(f"Failed to retrieve matches: {e}")
        return []
    finally:
        session.close()

def log_application(project: Dict[str, Any], match_data: Dict[str, Any], email_data: Dict[str, Any], status: str = "pending"):
    """Log a new application or update existing."""
    session = SessionLocal()
    try:
        application = Application(
            project_id=project.get("id"),
            project_title=project.get("title"),
            company=project.get("company"),
            match_score=match_data.get("overall_score", 0),
            status=status,
            sent_at=datetime.now() if status == "sent" else None,
            email_subject=email_data.get("subject"),
            email_body=email_data.get("body")
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        return application.id
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to log application: {e}")
        return None
    finally:
        session.close()

def update_application_status(app_id: int, status: str):
    session = SessionLocal()
    try:
        app = session.query(Application).filter(Application.id == app_id).first()
        if app:
            app.status = status
            if status == "sent":
                app.sent_at = datetime.now()
            elif status == "responded":
                app.response_at = datetime.now()
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update application {app_id}: {e}")
    finally:
        session.close()

def get_application_history(limit: int = 100) -> List[Dict[str, Any]]:
    session = SessionLocal()
    try:
        apps = session.query(Application).order_by(Application.id.desc()).limit(limit).all()
        return [{
            "id": a.id,
            "project_title": a.project_title,
            "company": a.company,
            "match_score": a.match_score,
            "status": a.status,
            "sent_at": a.sent_at,
            "response_at": a.response_at
        } for a in apps]
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []
    finally:
        session.close()

def get_statistics() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        stats = {}
        stats["total_applications"] = session.query(Application).count()
        stats["sent_emails"] = session.query(Application).filter(Application.status == 'sent').count()
        stats["responses"] = session.query(Application).filter(Application.status == 'responded').count()
        
        avg_score = session.query(func.avg(Application.match_score)).scalar()
        stats["avg_match_score"] = round(avg_score, 1) if avg_score else 0
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {}
    finally:
        session.close()

def get_cached_projects(file_hash: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve projects from cache by file hash."""
    session = SessionLocal()
    try:
        cache_entry = session.query(ProjectCache).filter(ProjectCache.hash == file_hash).first()
        if cache_entry:
            return cache_entry.projects
        return None
    except Exception as e:
        logger.error(f"Failed to get cached projects: {e}")
        return None
    finally:
        session.close()

def save_cached_projects(file_hash: str, projects: List[Dict[str, Any]]):
    """Save projects to cache."""
    session = SessionLocal()
    try:
        cache_entry = ProjectCache(hash=file_hash, projects=projects, created_at=datetime.now())
        session.merge(cache_entry) # Use merge to update if exists
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save cached projects: {e}")
    finally:
        session.close()

# --- Hybrid Matching Database Functions ---

def get_project_embeddings(project_ids: List[str]) -> Dict[str, np.ndarray]:
    """Bulk fetch cached embeddings."""
    session = SessionLocal()
    try:
        embeddings = session.query(ProjectEmbedding).filter(ProjectEmbedding.project_id.in_(project_ids)).all()
        return {e.project_id: pickle.loads(e.embedding) for e in embeddings}
    except Exception as e:
        logger.error(f"Failed to get project embeddings: {e}")
        return {}
    finally:
        session.close()

def save_project_embeddings(embeddings_map: Dict[str, Any]): # project_id -> (embedding, text_hash)
    """Bulk save project embeddings."""
    session = SessionLocal()
    try:
        for pid, (emb, thash) in embeddings_map.items():
            entry = ProjectEmbedding(
                project_id=pid,
                embedding=pickle.dumps(emb),
                text_hash=thash,
                created_at=datetime.now()
            )
            session.merge(entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save project embeddings: {e}")
    finally:
        session.close()

def get_cv_embedding(cv_hash: str) -> Optional[np.ndarray]:
    """Fetch cached CV embedding."""
    session = SessionLocal()
    try:
        entry = session.query(CVEmbedding).filter(CVEmbedding.cv_hash == cv_hash).first()
        if entry:
            return pickle.loads(entry.embedding)
        return None
    except Exception as e:
        logger.error(f"Failed to get CV embedding: {e}")
        return None
    finally:
        session.close()

def save_cv_embedding(cv_hash: str, embedding: np.ndarray):
    """Cache CV embedding."""
    session = SessionLocal()
    try:
        entry = CVEmbedding(cv_hash=cv_hash, embedding=pickle.dumps(embedding), created_at=datetime.now())
        session.merge(entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save CV embedding: {e}")
    finally:
        session.close()

def get_cached_match(cv_hash: str, project_id: str) -> Optional[Dict[str, Any]]:
    """Check if match exists."""
    session = SessionLocal()
    try:
        entry = session.query(MatchCache).filter(
            MatchCache.cv_hash == cv_hash,
            MatchCache.project_id == project_id
        ).first()
        if entry:
            return entry.result_json
        return None
    except Exception as e:
        logger.error(f"Failed to get cached match: {e}")
        return None
    finally:
        session.close()

def save_cached_match(cv_hash: str, project_id: str, result: Dict[str, Any]):
    """Store Gemini result."""
    session = SessionLocal()
    try:
        entry = MatchCache(
            cv_hash=cv_hash,
            project_id=project_id,
            score=result.get("overall_score", 0),
            result_json=result,
            created_at=datetime.now()
        )
        session.merge(entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save cached match: {e}")
    finally:
        session.close()
