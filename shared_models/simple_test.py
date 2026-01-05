#!/usr/bin/env python3
"""
Simple test to verify source metadata database works.
"""

import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from source_metadata_models import SourceMetadata
from source_metadata_db import get_source_metadata_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_source_metadata_database():
    """Test that source metadata database works correctly"""

    logger.info("Testing source metadata database...")

    with get_source_metadata_session() as session:
        # Test 1: Count total records
        total_count = session.query(SourceMetadata).count()
        logger.info(f"✓ Total source metadata records: {total_count}")

        # Test 2: Get specific record
        sudanile = session.query(SourceMetadata).filter(
            SourceMetadata.matched_domain == 'sudanile.com'
        ).first()

        if sudanile:
            logger.info(f"✓ Found Sudanile: {sudanile.outlet_name}")
            logger.info(f"  - Founded: {sudanile.founded_year}")
            logger.info(f"  - Bias: {sudanile.bias}")
            logger.info(f"  - Country: {sudanile.headquarters_country}")
        else:
            logger.error("✗ Sudanile not found")
            return False

        # Test 3: Test search functionality
        sudan_sources = session.query(SourceMetadata).filter(
            SourceMetadata.outlet_name.ilike('%sudan%')
        ).all()
        logger.info(f"✓ Found {len(sudan_sources)} sources with 'Sudan' in name")

        # Test 4: Test bias distribution
        from sqlalchemy import func
        bias_results = session.query(
            SourceMetadata.bias,
            func.count(SourceMetadata.id)
        ).group_by(SourceMetadata.bias).all()

        bias_dist = {bias or 'Unknown': count for bias, count in bias_results}
        logger.info(f"✓ Bias distribution: {bias_dist}")

    logger.info("All database tests passed! ✓")
    return True

if __name__ == "__main__":
    success = test_source_metadata_database()
    if not success:
        exit(1)
