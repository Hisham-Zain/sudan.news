import os
import platform
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from absolute path
    load_dotenv('/var/www/sudanese_news/shared/.env')

# Default database URL
DEFAULT_DB_URL = 'sqlite:////var/www/sudanese_news/shared/news_aggregator.db' if platform.system() != 'Windows' else 'sqlite:///../shared_models/news_aggregator.db'

def get_database_url() -> str:
    """Get database URL from environment or use default"""
    return os.getenv('DATABASE_URL', DEFAULT_DB_URL)

import logging

logger = logging.getLogger(__name__)

def create_engine_instance():
    """Create SQLAlchemy engine"""
    db_url = get_database_url()
    # Mask password if present
    safe_url = db_url
    if '@' in db_url:
        try:
            prefix = db_url.split('@')[0]
            suffix = db_url.split('@')[1]
            # This is a very basic mask, assuming standard URL format
            # protocol://user:pass@host...
            if ':' in prefix and '//' in prefix:
                protocol_part = prefix.split('//')[0]
                user_pass = prefix.split('//')[1]
                if ':' in user_pass:
                    user = user_pass.split(':')[0]
                    safe_url = f"{protocol_part}//{user}:****@{suffix}"
        except:
            pass # Fallback to showing full URL if parsing fails (or just don't log it)
            
    logger.info(f"Connecting to database: {safe_url}")
    return create_engine(db_url, echo=False)  # Set echo=True for debugging

# Create engine
engine = create_engine_instance()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session() -> Session:
    """Get a database session"""
    return SessionLocal()

def get_db():
    """Dependency for FastAPI-style dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
