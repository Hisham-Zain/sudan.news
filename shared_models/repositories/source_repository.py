from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..models import Source
from ..source_metadata_db import get_source_metadata_session
from .source_metadata_repository import SourceMetadataRepository

class SourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_source(self, url: str, name: str = None, language: str = 'ar', bias: str = None) -> Source:
        """Get existing source or create new one"""
        source = self.session.query(Source).filter(Source.url == url).first()
        if source:
            return source

        if not name:
            name = url  # Use URL as name if not provided

        source = Source(name=name, url=url, language=language, bias=bias)
        self.session.add(source)
        self.session.flush()
        return source

    def get_by_id(self, source_id: int) -> Optional[Source]:
        """Get source by ID"""
        return self.session.query(Source).filter(Source.id == source_id).first()

    def get_by_url(self, url: str) -> Optional[Source]:
        """Get source by URL"""
        return self.session.query(Source).filter(Source.url == url).first()

    def get_all_sources(self) -> List[Source]:
        """Get all sources"""
        return self.session.query(Source).all()

    def update_source(self, source_id: int, name: str = None, language: str = None) -> bool:
        """Update source information"""
        source = self.get_by_id(source_id)
        if not source:
            return False

        if name is not None:
            source.name = name
        if language is not None:
            source.language = language

        self.session.commit()
        return True

    def get_source_details(self, source_id: int, limit: int = 20):
        """Get source details with recent articles"""
        from ..models import Article
        from sqlalchemy import desc

        source = self.get_by_id(source_id)
        if not source:
            return None

        # Get recent articles from this source
        recent_articles = self.session.query(Article).filter(
            Article.source_id == source_id
        ).order_by(desc(Article.published_at)).limit(limit).all()

        # Try to get detailed metadata from the new database
        metadata_details = None
        with get_source_metadata_session() as metadata_session:
            metadata_repo = SourceMetadataRepository(metadata_session)
            metadata_details = metadata_repo.get_metadata_dict_by_domain(source.url)

        # Merge data from both databases
        result = {
            'id': source.id,
            'name': source.name,
            'url': source.url,
            'language': source.language,
            'recent_articles': [{
                'id': article.id,
                'headline': article.headline,
                'description': article.description,
                'published_at': article.published_at,
                'article_url': article.article_url,
                'image_url': article.image_url,
                'category': article.category
            } for article in recent_articles],
            'total_articles': len(source.articles) if hasattr(source, 'articles') else 0
        }

        # Use detailed metadata if available, otherwise fall back to basic source data
        if metadata_details:
            result.update({
                'outlet_name': metadata_details.get('outlet_name', source.name),
                'owner': metadata_details.get('ownership_structure', ''),
                'founded_at': metadata_details.get('founded_year', ''),
                'hq_location': self._format_hq_location(metadata_details),
                'bias': metadata_details.get('bias', source.bias or 'Neutral'),
                'political_alignment': metadata_details.get('political_alignment', ''),
                'credibility_rating': metadata_details.get('credibility_rating', ''),
                'funding_model': metadata_details.get('funding_model', ''),
                'target_audience': metadata_details.get('target_audience', ''),
                'verification_status': metadata_details.get('verification_status', ''),
                'has_detailed_metadata': True
            })
        else:
            # Fallback to basic source data
            result.update({
                'outlet_name': source.name,
                'owner': source.owner or '',
                'founded_at': source.founded_at or '',
                'hq_location': source.hq_location or '',
                'bias': source.bias or 'Neutral',
                'political_alignment': '',
                'credibility_rating': '',
                'funding_model': '',
                'target_audience': '',
                'verification_status': '',
                'has_detailed_metadata': False
            })

        return result

    def _format_hq_location(self, metadata_details: Dict[str, Any]) -> str:
        """Format headquarters location from metadata"""
        city = metadata_details.get('headquarters_city')
        country = metadata_details.get('headquarters_country')

        if city and country:
            return f"{city}, {country}"
        elif country:
            return country
        elif city:
            return city
        else:
            return ''
