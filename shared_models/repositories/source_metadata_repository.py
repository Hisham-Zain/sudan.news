from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..source_metadata_models import SourceMetadata

class SourceMetadataRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_domain(self, domain: str) -> Optional[SourceMetadata]:
        """Get source metadata by domain"""
        return self.session.query(SourceMetadata).filter(
            SourceMetadata.matched_domain == domain
        ).first()

    def get_by_id(self, metadata_id: int) -> Optional[SourceMetadata]:
        """Get source metadata by ID"""
        return self.session.query(SourceMetadata).filter(
            SourceMetadata.id == metadata_id
        ).first()

    def get_all_metadata(self) -> List[SourceMetadata]:
        """Get all source metadata"""
        return self.session.query(SourceMetadata).all()

    def search_by_name(self, name: str, limit: int = 10) -> List[SourceMetadata]:
        """Search source metadata by outlet name"""
        return self.session.query(SourceMetadata).filter(
            SourceMetadata.outlet_name.ilike(f'%{name}%')
        ).limit(limit).all()

    def get_metadata_dict_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get source metadata as dictionary by domain"""
        metadata = self.get_by_domain(domain)
        return metadata.to_dict() if metadata else None

    def create_metadata(self, **kwargs) -> SourceMetadata:
        """Create new source metadata record"""
        metadata = SourceMetadata(**kwargs)
        self.session.add(metadata)
        self.session.flush()
        return metadata

    def update_metadata(self, metadata_id: int, **kwargs) -> bool:
        """Update source metadata record"""
        metadata = self.get_by_id(metadata_id)
        if not metadata:
            return False

        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        metadata.updated_at = kwargs.get('updated_at', metadata.updated_at)
        self.session.commit()
        return True

    def delete_metadata(self, metadata_id: int) -> bool:
        """Delete source metadata record"""
        metadata = self.get_by_id(metadata_id)
        if not metadata:
            return False

        self.session.delete(metadata)
        self.session.commit()
        return True

    def get_bias_distribution(self) -> Dict[str, int]:
        """Get bias distribution across all sources"""
        from sqlalchemy import func

        results = self.session.query(
            SourceMetadata.bias,
            func.count(SourceMetadata.id)
        ).group_by(SourceMetadata.bias).all()

        return {bias or 'Unknown': count for bias, count in results}

    def get_sources_by_country(self, country: str) -> List[SourceMetadata]:
        """Get sources by headquarters country"""
        return self.session.query(SourceMetadata).filter(
            SourceMetadata.headquarters_country.ilike(f'%{country}%')
        ).all()

    def get_sources_by_credibility(self, credibility_rating: str) -> List[SourceMetadata]:
        """Get sources by credibility rating"""
        return self.session.query(SourceMetadata).filter(
            SourceMetadata.credibility_rating.ilike(f'%{credibility_rating}%')
        ).all()
