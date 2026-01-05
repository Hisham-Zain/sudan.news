#!/usr/bin/env python3
"""
Test script to verify source metadata integration works correctly.
"""

import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from repositories.source_repository import SourceRepository
from repositories.source_metadata_repository import SourceMetadataRepository
from db import get_session
from source_metadata_db import get_source_metadata_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_source_metadata_integration():
    """Test that source metadata integration works correctly"""

    # Test 1: Check if we can fetch metadata directly
    logger.info("Test 1: Fetching metadata directly from source metadata database")
    with get_source_metadata_session() as session:
        metadata_repo = SourceMetadataRepository(session)
        metadata = metadata_repo.get_metadata_dict_by_domain('sudanile.com')
        if metadata:
            logger.info(f"✓ Found metadata for sudanile.com: {metadata.get('outlet_name')}")
        else:
            logger.error("✗ No metadata found for sudanile.com")
            return False

    # Test 2: Check if source repository can merge data
    logger.info("Test 2: Testing source repository integration")
    with get_session() as session:
        source_repo = SourceRepository(session)

        # Find a source that should have metadata
        sources = source_repo.get_all_sources()
        test_source = None
        for source in sources:
            if source.url == 'sudanile.com':
                test_source = source
                break

        if not test_source:
            logger.warning("No source found with URL sudanile.com in main database, creating test source")
            # Create a test source
            test_source = source_repo.get_or_create_source('sudanile.com', 'Sudanile')
            session.commit()

        # Get source details (should merge with metadata)
        details = source_repo.get_source_details(test_source.id)
        if details:
            logger.info(f"✓ Source details retrieved: {details.get('name')}")
            logger.info(f"  - Has detailed metadata: {details.get('has_detailed_metadata')}")
            if details.get('has_detailed_metadata'):
                logger.info(f"  - Outlet name: {details.get('outlet_name')}")
                logger.info(f"  - Founded year: {details.get('founded_at')}")
                logger.info(f"  - Bias: {details.get('bias')}")
            else:
                logger.info("  - Using fallback basic data")
        else:
            logger.error("✗ Failed to get source details")
            return False

    # Test 3: Check metadata repository methods
    logger.info("Test 3: Testing metadata repository methods")
    with get_source_metadata_session() as session:
        metadata_repo = SourceMetadataRepository(session)

        # Test search
        results = metadata_repo.search_by_name('Sudan', limit=5)
        logger.info(f"✓ Found {len(results)} sources matching 'Sudan'")

        # Test bias distribution
        bias_dist = metadata_repo.get_bias_distribution()
        logger.info(f"✓ Bias distribution: {bias_dist}")

    logger.info("All tests passed! ✓")
    return True

if __name__ == "__main__":
    success = test_source_metadata_integration()
    if not success:
        exit(1)
