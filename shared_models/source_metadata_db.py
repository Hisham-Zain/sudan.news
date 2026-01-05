import os
import platform
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from absolute path
    load_dotenv('/var/www/sudanese.news/shared/.env')

# Default database URL for source metadata
DEFAULT_SOURCE_METADATA_DB_URL = 'sqlite:///../shared_models/source_details.db' if platform.system() == 'Windows' else 'sqlite:////var/www/sudanese_news/shared/source_details.db'

def get_source_metadata_database_url() -> str:
    """Get source metadata database URL from environment or use default"""
    return os.getenv('SOURCE_METADATA_DATABASE_URL', DEFAULT_SOURCE_METADATA_DB_URL)

import logging

logger = logging.getLogger(__name__)

def create_source_metadata_engine():
    """Create SQLAlchemy engine for source metadata database"""
    db_url = get_source_metadata_database_url()
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

    logger.info(f"Connecting to source metadata database: {safe_url}")
    return create_engine(db_url, echo=False)  # Set echo=True for debugging

# Create engine for source metadata
source_metadata_engine = create_source_metadata_engine()

# Create session factory for source metadata
SourceMetadataSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=source_metadata_engine)

def get_source_metadata_session() -> Session:
    """Get a source metadata database session"""
    return SourceMetadataSessionLocal()

def get_source_metadata_db():
    """Dependency for FastAPI-style dependency injection"""
    db = SourceMetadataSessionLocal()
    try:
        yield db
    finally:
        db.close()
