#!/usr/bin/env python3
"""
Script to migrate source details from news_details.jsonl to the new source_metadata database.
"""

import json
import logging
from datetime import datetime
from source_metadata_models import SourceMetadata
from source_metadata_db import get_source_metadata_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_headquarters(headquarters_data):
    """Parse headquarters data from JSONL format"""
    if not headquarters_data or not isinstance(headquarters_data, dict):
        return None, None

    city = headquarters_data.get('city', '')
    country = headquarters_data.get('country', '')

    # Clean up common patterns
    if city == 'Unknown' or city == '':
        city = None
    if country == 'Unknown' or country == '':
        country = None

    return city, country

def map_political_alignment_to_bias(political_alignment):
    """Map political alignment to bias for backward compatibility"""
    if not political_alignment:
        return 'Neutral'

    alignment_lower = political_alignment.lower()

    if 'pro-democracy' in alignment_lower or 'independent' in alignment_lower:
        return 'Neutral'
    elif 'pro-saf' in alignment_lower or 'anti-rsf' in alignment_lower:
        return 'Pro-SAF'
    elif 'oppose-saf' in alignment_lower or 'anti-saf' in alignment_lower:
        return 'Oppose-SAF'
    else:
        return 'Neutral'

def migrate_source_details():
    """Migrate source details from JSONL file to database"""
    jsonl_file = 'news_details.jsonl'

    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"File {jsonl_file} not found!")
        return

    # Split content by JSON object boundaries (each starts with '{')
    json_objects = content.strip().split('\n\n')

    logger.info(f"Found {len(json_objects)} source records to migrate")

    with get_source_metadata_session() as session:
        migrated_count = 0
        skipped_count = 0

        for obj_num, json_str in enumerate(json_objects, 1):
            try:
                # Clean up the JSON string
                json_str = json_str.strip()
                if not json_str:
                    continue

                data = json.loads(json_str)

                # Extract domain from matched_domain
                matched_domain = data.get('matched_domain', '').strip()
                if not matched_domain:
                    logger.warning(f"Object {obj_num}: No matched_domain found, skipping")
                    skipped_count += 1
                    continue

                # Check if already exists
                existing = session.query(SourceMetadata).filter(
                    SourceMetadata.matched_domain == matched_domain
                ).first()

                if existing:
                    logger.info(f"Object {obj_num}: {matched_domain} already exists, skipping")
                    skipped_count += 1
                    continue

                # Parse headquarters data
                hq_city, hq_country = parse_headquarters(data.get('headquarters'))

                # Map political alignment to bias
                political_alignment = data.get('political_alignment', '')
                bias = map_political_alignment_to_bias(political_alignment)

                # Create new source metadata record
                source_metadata = SourceMetadata(
                    matched_domain=matched_domain,
                    outlet_name=data.get('outlet_name', ''),
                    founded_year=data.get('founded_year', ''),
                    headquarters_city=hq_city,
                    headquarters_country=hq_country,
                    ownership_structure=data.get('ownership_structure', ''),
                    funding_model=data.get('funding_model', ''),
                    political_alignment=political_alignment,
                    credibility_rating=data.get('credibility_rating', ''),
                    target_audience=data.get('target_audience', ''),
                    verification_status=data.get('verification_status', ''),
                    language='ar',  # Default to Arabic
                    bias=bias,
                    created_at=datetime.utcnow().isoformat(),
                    updated_at=datetime.utcnow().isoformat()
                )

                session.add(source_metadata)
                migrated_count += 1
                logger.info(f"Object {obj_num}: Migrated {matched_domain}")

            except json.JSONDecodeError as e:
                logger.error(f"Object {obj_num}: Invalid JSON - {e}")
                skipped_count += 1
            except Exception as e:
                logger.error(f"Object {obj_num}: Error processing {matched_domain} - {e}")
                skipped_count += 1

        # Commit all changes
        session.commit()

        logger.info(f"Migration completed: {migrated_count} migrated, {skipped_count} skipped")

if __name__ == "__main__":
    migrate_source_details()
