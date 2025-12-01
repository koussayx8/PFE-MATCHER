from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine, LargeBinary, UniqueConstraint, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String)
    project_title = Column(String)
    company = Column(String)
    match_score = Column(Integer)
    status = Column(String, default='pending')  # pending, queued, sent, responded, rejected
    sent_at = Column(DateTime, nullable=True)
    response_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    email_subject = Column(Text, nullable=True)
    email_body = Column(Text, nullable=True)

class ProjectCache(Base):
    __tablename__ = 'project_cache'

    hash = Column(String, primary_key=True)
    projects = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)

class ProjectEmbedding(Base):
    __tablename__ = 'project_embeddings'

    project_id = Column(String, primary_key=True)
    embedding = Column(LargeBinary) # PickleType or LargeBinary for numpy array
    text_hash = Column(String)
    created_at = Column(DateTime, default=datetime.now)

class CVEmbedding(Base):
    __tablename__ = 'cv_embeddings'

    cv_hash = Column(String, primary_key=True)
    embedding = Column(LargeBinary)
    created_at = Column(DateTime, default=datetime.now)

class MatchCache(Base):
    __tablename__ = 'match_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cv_hash = Column(String, index=True)
    project_id = Column(String, index=True)
    score = Column(Float)
    result_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (UniqueConstraint('cv_hash', 'project_id', name='uix_cv_project'),)

class UploadedDocument(Base):
    __tablename__ = 'uploaded_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_hash = Column(String, unique=True, index=True)
    original_filename = Column(String)
    file_path = Column(String)
    file_size = Column(Integer)
    mime_type = Column(String)
    document_type = Column(String) # 'cv', 'pfe_book', 'other'
    extracted_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.now)

class Match(Base):
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String)
    project_title = Column(String)
    company = Column(String)
    score = Column(Integer)
    recommendation = Column(Text)
    matching_points = Column(JSON)  # Stores list of strings
    gaps = Column(JSON)  # Stores list of strings
    created_at = Column(DateTime, default=datetime.now)
