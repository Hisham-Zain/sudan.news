from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import TypeDecorator
import json
from typing import Any, Dict, List

Base = declarative_base()

class JSONType(TypeDecorator):
    """Custom JSON type that works with both PostgreSQL and SQLite"""
    impl = Text

    def process_bind_param(self, value: Any, dialect) -> str:
        if value is None:
            return None
        if dialect.name == 'postgresql':
            # PostgreSQL has native JSON support
            return value
        # For SQLite, serialize to JSON string
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if dialect.name == 'postgresql':
            # PostgreSQL returns JSON objects directly
            return value
        # For SQLite, parse JSON string
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

class SourceMetadata(Base):
    __tablename__ = 'source_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    matched_domain = Column(String, unique=True)  # URL/domain identifier
    outlet_name = Column(String)
    founded_year = Column(String)
    headquarters_city = Column(String)
    headquarters_country = Column(String)
    ownership_structure = Column(Text)
    funding_model = Column(Text)
    political_alignment = Column(String)
    credibility_rating = Column(String)
    target_audience = Column(String)
    verification_status = Column(String)
    language = Column(String, default='ar')
    bias = Column(String)  # For backward compatibility
    created_at = Column(String)
    updated_at = Column(String)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'matched_domain': self.matched_domain,
            'outlet_name': self.outlet_name,
            'founded_year': self.founded_year,
            'headquarters_city': self.headquarters_city,
            'headquarters_country': self.headquarters_country,
            'ownership_structure': self.ownership_structure,
            'funding_model': self.funding_model,
            'political_alignment': self.political_alignment,
            'credibility_rating': self.credibility_rating,
            'target_audience': self.target_audience,
            'verification_status': self.verification_status,
            'language': self.language,
            'bias': self.bias,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
