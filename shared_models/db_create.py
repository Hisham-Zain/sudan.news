#!/usr/bin/env python3
"""
Database Creation Script for Sudanese News Aggregator

This script provides a quick way to create and populate the database
for development and testing purposes. It uses SQLAlchemy's create_all()
instead of Alembic migrations for simplicity.

Usage:
    python db_create.py

This is suitable for:
- Quick development setup
- SQLite databases
- Testing environments
- Initial project setup

For production deployments with schema versioning, use Alembic migrations instead.
"""

import os
import sys
import platform
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from absolute path
    load_dotenv('/var/www/sudanese.news/shared/.env')

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

from shared_models.models import Base
from shared_models.db import engine, get_session
from shared_models.repositories.source_repository import SourceRepository
from shared_models.repositories.article_repository import ArticleRepository
from shared_models.repositories.entity_repository import EntityRepository

def create_database():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")

def populate_sources():
    """Populate database with sources from news_bias.json"""
    print("Populating sources from news_bias.json...")

    # Create session
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Initialize repository
        source_repo = SourceRepository(session)

        # Load sources from news_bias.json
        news_bias_file = os.path.join(script_dir, 'news_bias.json')
        with open(news_bias_file, 'r', encoding='utf-8') as f:
            sources_data = json.load(f)

        sources_created = 0
        for source_data in sources_data:
            source = source_repo.get_or_create_source(
                url=source_data["website_url"],
                name=source_data["Source_name"],
                bias=source_data["Bias"]
            )
            sources_created += 1

        session.commit()
        print(f"✓ Successfully populated {sources_created} sources with bias information")

    except Exception as e:
        session.rollback()
        print(f"✗ Error populating sources: {e}")
        raise
    finally:
        session.close()

def main():
    """Main function"""
    print("Sudanese News Aggregator - Database Creation Script")
    print("=" * 50)

    # Check database URL
    from shared_models.db import get_database_url
    db_url = get_database_url()
    print(f"Database URL: {db_url}")

    if "sqlite" not in db_url.lower():
        print("⚠️  Warning: This script is designed for SQLite databases.")
        print("   For PostgreSQL or other databases, use Alembic migrations instead.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    # Create database
    create_database()
    # Populate sources
    populate_sources()


    print("\n✓ Database setup complete!")
    print("\nNext steps:")
    print("1. Run the pipeline: cd ../sudan-news-pipeline && python src/run_pipeline.py run-once")
    print("2. Start the API: cd ../sudan-news-api && python src/app.py")
    print("3. Visit http://localhost:5000")

if __name__ == "__main__":
    main()
