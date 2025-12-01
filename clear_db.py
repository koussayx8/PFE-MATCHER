import logging
from src.data_management.database import SessionLocal, engine
from src.data_management.models import Base, Match, ProjectCache, MatchCache, ProjectEmbedding, CVEmbedding, Application
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_database():
    """
    Clears all data from the database tables but keeps the schema.
    Does NOT delete any files from the disk.
    """
    session = SessionLocal()
    try:
        logger.info("Starting database cleanup...")
        
        # List of models to clear
        models = [Match, ProjectCache, MatchCache, ProjectEmbedding, CVEmbedding, Application]
        
        for model in models:
            table_name = model.__tablename__
            count = session.query(model).delete()
            logger.info(f"Deleted {count} records from table '{table_name}'.")
            
        session.commit()
        logger.info("Database cleanup completed successfully!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to clear database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete all matches, cache, and embeddings from the database.")
    print("Files in 'data/uploads' will NOT be deleted.")
    confirm = input("Are you sure you want to proceed? (y/n): ")
    
    if confirm.lower() == 'y':
        clear_database()
    else:
        print("Operation cancelled.")
