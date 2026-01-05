#!/usr/bin/env python3
"""
Script to create the source metadata database and tables.
"""

from source_metadata_models import Base
from source_metadata_db import source_metadata_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_source_metadata_database():
    """Create the source metadata database and tables"""
    try:
        logger.info("Creating source metadata database tables...")
        Base.metadata.create_all(bind=source_metadata_engine)
        logger.info("Source metadata database created successfully!")
    except Exception as e:
        logger.error(f"Error creating source metadata database: {e}")
        raise

if __name__ == "__main__":
    create_source_metadata_database()
