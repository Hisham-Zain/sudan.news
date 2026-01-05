# Source Metadata Database

This document describes the new source metadata database architecture that separates static source details from the dynamic aggregator database.

## Overview

The news aggregator system now uses two separate databases:

1. **Main Database** (`news_aggregator.db`): Contains dynamic data used by the aggregator (articles, sources, clusters, etc.)
2. **Source Metadata Database** (`source_details.db`): Contains comprehensive static metadata about news sources

## Database Schema

### SourceMetadata Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-incrementing primary key |
| matched_domain | String (Unique) | Domain/URL identifier for matching |
| outlet_name | String | Full name of the news outlet |
| founded_year | String | Year the outlet was founded |
| headquarters_city | String | City where headquarters is located |
| headquarters_country | String | Country where headquarters is located |
| ownership_structure | Text | Details about ownership and corporate structure |
| funding_model | Text | How the outlet is funded |
| political_alignment | String | Political alignment description |
| credibility_rating | String | Credibility assessment |
| target_audience | String | Target audience description |
| verification_status | String | Verification status and confidence level |
| language | String | Primary language (default: 'ar') |
| bias | String | Bias classification for backward compatibility |
| created_at | String | ISO timestamp when record was created |
| updated_at | String | ISO timestamp when record was last updated |

## Architecture Benefits

1. **Separation of Concerns**: Static metadata is separated from dynamic aggregator data
2. **Performance**: Smaller, focused databases for specific use cases
3. **Maintainability**: Source metadata can be updated without affecting aggregator operations
4. **Scalability**: Easy to add new metadata fields without impacting core functionality
5. **Safety**: No risk of breaking aggregator functionality when updating source details

## Usage

### Direct Database Access

```python
from source_metadata_db import get_source_metadata_session
from repositories.source_metadata_repository import SourceMetadataRepository

with get_source_metadata_session() as session:
    repo = SourceMetadataRepository(session)
    metadata = repo.get_metadata_dict_by_domain('sudanile.com')
```

### Integrated API Access

The existing `SourceRepository.get_source_details()` method automatically merges data from both databases:

```python
from db import get_session
from repositories.source_repository import SourceRepository

with get_session() as session:
    repo = SourceRepository(session)
    source_details = repo.get_source_details(source_id)
    # Returns merged data with detailed metadata if available
```

## Data Migration

Source details were migrated from `news_details.jsonl` using the migration script:

```bash
cd shared_models
python migrate_source_details.py
```

This script:
- Parses the JSONL file (correctly handling multi-line JSON objects)
- Maps political alignment to bias for backward compatibility
- Creates records in the new source metadata database

## API Integration

The API endpoints continue to work unchanged, but now provide richer source details:

- `/source/<source_id>`: Returns comprehensive source information
- Source details in article responses include enhanced metadata
- Backward compatibility maintained for existing mobile app clients

## Files Created

- `source_metadata_models.py`: SQLAlchemy models for source metadata
- `source_metadata_db.py`: Database connection and session management
- `create_source_metadata_db.py`: Database schema creation script
- `migrate_source_details.py`: Data migration from JSONL to database
- `repositories/source_metadata_repository.py`: Repository for metadata operations
- Updated `repositories/source_repository.py`: Enhanced to merge data from both databases

## Testing

Run the simple test to verify database functionality:

```bash
cd shared_models
python simple_test.py
```

## Environment Variables

Optional environment variables for configuration:

- `SOURCE_METADATA_DATABASE_URL`: Override default database URL for source metadata

## Future Enhancements

- Add source logo URLs
- Include social media handles
- Add editorial staff information
- Include historical bias changes
- Add fact-checking organization ratings
