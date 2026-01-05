from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, cast, Text, or_
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
from ..models import Cluster, Article, cluster_articles, Entity
from ..timezone_utils import now, format_datetime

class ClusterRepository:
    def __init__(self, session: Session):
        self.session = session

    def find_best_cluster_for_vector(self, embedding_vector: np.ndarray,
                                   similarity_threshold: float = 0.5,
                                   time_window_hours: int = 72) -> Optional[Tuple[Cluster, float]]:
        """Find the best matching cluster for a given embedding vector"""
        from datetime import timedelta
        cutoff_time = now() - timedelta(hours=time_window_hours)

        # Get active clusters within time window
        active_clusters = self.session.query(Cluster).filter(
            Cluster.created_at >= cutoff_time.isoformat()
        ).all()

        best_cluster = None
        highest_similarity = -1.0

        for cluster in active_clusters:
            # Get articles in this cluster to compute representative vector
            cluster_articles_data = self.session.query(cluster_articles).filter(
                cluster_articles.c.cluster_id == cluster.id
            ).all()

            if not cluster_articles_data:
                continue

            # Simple average of article embeddings (would need to store embeddings in DB)
            # For now, return None as we don't have embeddings stored
            # In production, you'd store embeddings and compute similarity here
            similarity = 0.0  # Placeholder

            if similarity > highest_similarity and similarity >= similarity_threshold:
                highest_similarity = similarity
                best_cluster = cluster

        return (best_cluster, highest_similarity) if best_cluster else None

    def create_cluster(self, title: str, number_of_sources: int,
                      published_at: str) -> Cluster:
        """Create a new cluster"""
        created_at = now().isoformat()
        cluster = Cluster(
            title=title,
            number_of_sources=number_of_sources,
            published_at=published_at,
            created_at=created_at
        )
        self.session.add(cluster)
        self.session.flush()
        return cluster

    def update_cluster_vector(self, cluster_id: int, new_embedding: np.ndarray):
        """Update cluster's representative vector (placeholder for future embedding storage)"""
        # In a full implementation, you'd store and update cluster embeddings
        pass

    def get_cluster_details(self, cluster_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed cluster information with articles and entities"""
        cluster = self.session.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            return None

        # Get articles in cluster
        articles_data = self.session.query(Article, cluster_articles.c.similarity_score).join(
            cluster_articles, Article.id == cluster_articles.c.article_id
        ).filter(cluster_articles.c.cluster_id == cluster_id).all()

        articles = []
        for article, similarity_score in articles_data:
            entities = article.get_entities(self.session)
            article_dict = {
                'id': article.id,
                'headline': article.headline,
                'description': article.description,
                'published_at': article.published_at,
                'article_url': article.article_url,
                'image_url': article.image_url,
                'source_id': article.source.id if article.source else None,
                'source_name': article.source.name if article.source else None,
                'source_url': article.source.url if article.source else None,
                'source_bias': article.source.bias if article.source else None,
                'source_owner': article.source.owner if article.source else None,
                'source_founded_at': article.source.founded_at if article.source else None,
                'source_hq_location': article.source.hq_location if article.source else None,
                'category': article.category,
                'similarity_score': similarity_score,
                'entities': None
            }

            if entities:
                article_dict['entities'] = {
                    'people': entities.people or [],
                    'cities': entities.cities or [],
                    'regions': entities.regions or [],
                    'countries': entities.countries or [],
                    'organizations': entities.organizations or [],
                    'political_parties_and_militias': entities.political_parties_and_militias or [],
                    'brands': entities.brands or [],
                    'job_titles': entities.job_titles or [],
                    'nlp_category': entities.category
                }

            articles.append(article_dict)

        # Calculate bias distribution
        total_articles = len(articles)
        bias_distribution = {
            'pro_saf': {
                'count': cluster.bias_coverage_pro,
                'percentage': round((cluster.bias_coverage_pro / total_articles * 100), 1) if total_articles > 0 else 0
            },
            'neutral': {
                'count': cluster.bias_coverage_neutral,
                'percentage': round((cluster.bias_coverage_neutral / total_articles * 100), 1) if total_articles > 0 else 0
            },
            'oppose_saf': {
                'count': cluster.bias_coverage_oppose,
                'percentage': round((cluster.bias_coverage_oppose / total_articles * 100), 1) if total_articles > 0 else 0
            }
        }

        return {
            'id': cluster.id,
            'title': cluster.title,
            'number_of_sources': cluster.number_of_sources,
            'published_at': cluster.published_at,
            'created_at': cluster.created_at,
            'articles': articles,
            'blindspot_type': cluster.blindspot_type,
            'bias_balance_score': cluster.bias_balance_score,
            'bias_distribution': bias_distribution,
            'is_trending': cluster.is_trending,
            'coverage_velocity': cluster.coverage_velocity
        }

    def get_recent_clusters(self, limit: int = 50, offset: int = 0) -> List[Cluster]:
        """Get recent clusters ordered by published date"""
        return self.session.query(Cluster).order_by(
            desc(Cluster.published_at)
        ).limit(limit).offset(offset).all()

    def get_total_clusters(self) -> int:
        """Get total number of clusters"""
        return self.session.query(func.count(Cluster.id)).scalar()

    def get_all_cities(self) -> List[str]:
        """Get list of all unique cities from entities"""
        # Fetch all cities lists
        # Note: This fetches all rows, which might be heavy if table is huge.
        # Optimization: In Postgres we could use distinct unnest.
        # For SQLite/Generic JSON, we fetch and process in Python.
        entities = self.session.query(Entity.cities).filter(
            Entity.cities.isnot(None)
        ).all()

        unique_cities = set()
        for entity in entities:
            if entity.cities:
                # entity.cities is already a list due to JSONType
                unique_cities.update(entity.cities)

        return sorted(list(unique_cities))

    def get_clusters_with_filters(self, query: str = None, has_entities: bool = False,
                                category: str = None, city: str = None,
                                limit: int = 50, offset: int = 0) -> Tuple[List[Cluster], int]:
        """Get clusters with search and filter options"""
        base_query = self.session.query(Cluster)

        conditions = []
        if query:
            base_query = base_query.filter(Cluster.title.like(f'%{query}%'))

        if has_entities:
            # Clusters that have articles with entities
            base_query = base_query.filter(
                Cluster.id.in_(
                    self.session.query(cluster_articles.c.cluster_id).join(
                        Article, cluster_articles.c.article_id == Article.id
                    ).join(Entity, Article.id == Entity.article_id)
                )
            )

        if category and category != 'all':
            # Map UI category to NLP category
            category_mapping = {
                'politics': 'سياسة',
                'economy': 'اقتصاد',
                'sports': 'رياضة',
                'security': 'أمن وعسكر',
                'culture': 'مجتمع وثقافة',
                'opinion': 'مقالات رأي'
            }
            nlp_category = category_mapping.get(category, category)

            base_query = base_query.filter(
                Cluster.id.in_(
                    self.session.query(cluster_articles.c.cluster_id).join(
                        Article, cluster_articles.c.article_id == Article.id
                    ).join(Entity, Article.id == Entity.article_id).filter(
                        Entity.category == nlp_category
                    )
                )
            )

        if city:
            # Filter by city in Entity.cities
            # Using LIKE for SQLite JSON text matching as a fallback/simple solution
            # For exact match in JSON array: like '%"City"%'
            base_query = base_query.filter(
                Cluster.id.in_(
                    self.session.query(cluster_articles.c.cluster_id).join(
                        Article, cluster_articles.c.article_id == Article.id
                    ).join(Entity, Article.id == Entity.article_id).filter(
                        cast(Entity.cities, Text).like(f'%"{city}"%')
                    )
                )
            )

        clusters = base_query.order_by(desc(Cluster.published_at)).limit(limit).offset(offset).all()

        # Get total count
        total = base_query.count()

        return clusters, total

    def calculate_blindspot(self, cluster_id: int) -> Optional[Dict[str, Any]]:
        """
        Calculate blindspot metrics for a cluster.
        
        Returns:
            dict: {
                'blindspot_type': str,
                'pro_count': int,
                'neutral_count': int,
                'oppose_count': int,
                'balance_score': float (0-1, where 1 is perfect balance)
            }
        """
        cluster = self.session.query(Cluster).get(cluster_id)
        if not cluster:
            return None
        
        bias_counts = {
            'pro': 0,
            'neutral': 0,
            'oppose': 0
        }
        
        # Count articles by source bias
        for article in cluster.articles:
            if article.source and article.source.bias:
                bias = article.source.bias.lower()
                if 'pro' in bias:
                    bias_counts['pro'] += 1
                elif 'oppose' in bias:
                    bias_counts['oppose'] += 1
                else:
                    bias_counts['neutral'] += 1
        
        total = sum(bias_counts.values())
        if total == 0:
            return None
        
        # Calculate percentages
        percentages = {
            k: (v / total * 100) for k, v in bias_counts.items()
        }
        
        # Determine blindspot type
        blindspot_type = 'BALANCED'
        
        # Criteria: >70% from one side, <15% from opposite
        if percentages['oppose'] > 70 and percentages['pro'] < 15:
            blindspot_type = 'PRO_SAF_BLINDSPOT'
        elif percentages['pro'] > 70 and percentages['oppose'] < 15:
            blindspot_type = 'OPPOSE_SAF_BLINDSPOT'
        elif percentages['neutral'] > 80 and total > 2:
            blindspot_type = 'NEUTRAL_ONLY'
        elif percentages['neutral'] < 20 and total > 3:
            blindspot_type = 'PARTISAN_STORY'
        
        # Calculate balance score (higher = more balanced)
        # Perfect balance would be 33.33% each
        ideal = 33.33
        variance = sum(abs(percentages[k] - ideal) for k in percentages.keys())
        balance_score = max(0, 1 - (variance / 100))
        
        return {
            'blindspot_type': blindspot_type,
            'pro_count': bias_counts['pro'],
            'neutral_count': bias_counts['neutral'],
            'oppose_count': bias_counts['oppose'],
            'balance_score': round(balance_score, 2)
        }

    def update_cluster_blindspot(self, cluster_id: int) -> bool:
        """Update cluster with calculated blindspot data."""
        metrics = self.calculate_blindspot(cluster_id)
        if not metrics:
            return False
        
        cluster = self.session.query(Cluster).get(cluster_id)
        if not cluster:
            return False
        
        cluster.blindspot_type = metrics['blindspot_type']
        cluster.bias_coverage_pro = metrics['pro_count']
        cluster.bias_coverage_neutral = metrics['neutral_count']
        cluster.bias_coverage_oppose = metrics['oppose_count']
        cluster.bias_balance_score = metrics['balance_score']
        
        self.session.flush()
        return True

    def calculate_trending(self, cluster_id: int) -> bool:
        """
        Calculate if a cluster is trending based on coverage velocity.
        
        Velocity = articles added in last 6 hours / articles added in previous 6 hours
        Trending if velocity > 1.5 (50% increase) and has at least 3 sources
        """
        from datetime import timedelta
        
        cluster = self.session.query(Cluster).get(cluster_id)
        if not cluster:
            return False
        
        current_time = now()
        six_hours_ago = current_time - timedelta(hours=6)
        twelve_hours_ago = current_time - timedelta(hours=12)
        
        # Count articles in last 6 hours vs previous 6 hours
        recent_count = 0
        previous_count = 0
        
        for article in cluster.articles:
            if article.created_at:
                try:
                    created = datetime.fromisoformat(article.created_at)
                    if created > six_hours_ago:
                        recent_count += 1
                    elif created > twelve_hours_ago:
                        previous_count += 1
                except:
                    pass
        
        # Calculate velocity
        if previous_count > 0:
            velocity = recent_count / previous_count
        elif recent_count > 0:
            velocity = float(recent_count)  # No previous coverage, high velocity
        else:
            velocity = 0.0
        
        # Update cluster
        cluster.coverage_velocity = round(velocity, 2)
        cluster.is_trending = velocity > 1.5 and cluster.number_of_sources >= 3
        cluster.last_coverage_check = current_time.isoformat()
        
        # Set first_seen_at if not already set
        if not cluster.first_seen_at:
            cluster.first_seen_at = cluster.created_at
        
        self.session.flush()
        return True

    def get_trending_clusters(self, limit: int = 10) -> List[Cluster]:
        """Get clusters that are currently trending."""
        from datetime import timedelta
        
        # Only consider clusters from last 48 hours
        cutoff = datetime.now() - timedelta(hours=48)
        cutoff_str = cutoff.isoformat()
        
        trending = self.session.query(Cluster)\
            .filter(Cluster.is_trending == True)\
            .filter(Cluster.published_at >= cutoff_str)\
            .order_by(desc(Cluster.coverage_velocity))\
            .limit(limit)\
            .all()
        
        return trending
