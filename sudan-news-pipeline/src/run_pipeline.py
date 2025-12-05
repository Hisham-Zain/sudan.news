#!/usr/bin/env python3
"""
Sudan News Pipeline CLI

Command-line interface for running the news aggregation and clustering pipeline.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from contextlib import contextmanager

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent)) # Also keep pipeline root for config
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'sudan-news-api' / 'src')) # Add API src for notification service

from shared_models.db import get_session
from shared_models.repositories.article_repository import ArticleRepository
from shared_models.repositories.cluster_repository import ClusterRepository
from shared_models.repositories.source_repository import SourceRepository
from shared_models.repositories.entity_repository import EntityRepository
from shared_models.models import Cluster

import config
from .aggregator import parse_feed, is_sudan_related, normalize_arabic
from .nlp_pipeline import analyze_text
from .clustering import preprocess_articles, cluster_articles

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import requests for API calls to notification service
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    logger.warning("Requests library not available for notifications")
    REQUESTS_AVAILABLE = False

@contextmanager
def pipeline_lock():
    """Context manager for pipeline locking to prevent concurrent runs"""
    if not HAS_FCNTL:
        # On Windows, skip locking
        logger.warning("File locking not available on this platform, skipping lock")
        yield
        return

    lock_path = Path(config.LOCK_FILE)
    lock_file = None

    try:
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("Pipeline lock acquired")
        yield
    except (OSError, BlockingIOError):
        logger.error("Pipeline is already running (lock file exists)")
        raise RuntimeError("Pipeline already running")
    finally:
        if lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            lock_path.unlink(missing_ok=True)
            logger.info("Pipeline lock released")

def aggregate_news():
    """Run news aggregation phase"""
    logger.info("Starting news aggregation")

    with get_session() as session:
        source_repo = SourceRepository(session)
        article_repo = ArticleRepository(session)
        entity_repo = EntityRepository(session)

        total_articles = 0

        for feed in config.FEEDS:
            source_url = feed['source']
            category = 'international' if source_url in config.INTERNATIONAL_SOURCES else 'local'

            # Get or create source
            source = source_repo.get_or_create_source(source_url, source_url)

            parsed_articles = parse_feed(feed['url'], feed['source'])
            inserted_count = 0

            for article_data in parsed_articles:
                if category == 'local' or (category == 'international' and is_sudan_related(
                    article_data['headline'] + ' ' + article_data['description'], source_url)):

                    published_at = article_data['published_at'] if article_data['published_at'] != "N/A" else None

                    # Insert article
                    article = article_repo.insert_article(
                        source_id=source.id,
                        headline=article_data['headline'],
                        description=article_data['description'],
                        published_at=published_at,
                        article_url=article_data['article_url'],
                        image_url=article_data['image_url'],
                        category=category
                    )

                    # Analyze text with NLP
                    text_to_analyze = article_data['headline'] + " " + article_data['description']
                    entities_json = analyze_text(text_to_analyze)
                    entities_result = json.loads(entities_json)

                    # Store entities
                    entity_repo.insert_entities(
                        article_id=article.id,
                        people=entities_result['people'],
                        cities=entities_result['cities'],
                        regions=entities_result['regions'],
                        countries=entities_result['countries'],
                        organizations=entities_result['organizations'],
                        political_parties_and_militias=entities_result['political_parties_and_militias'],
                        brands=entities_result['brands'],
                        job_titles=entities_result['job_titles'],
                        category=entities_result['category']
                    )

                    inserted_count += 1

            total_articles += inserted_count
            logger.info(f"Processed {inserted_count} articles from {source_url}")

        session.commit()
        logger.info(f"Aggregation complete: {total_articles} articles processed")

def cluster_news():
    """Run event clustering phase"""
    logger.info("Starting event clustering")

    with get_session() as session:
        article_repo = ArticleRepository(session)
        cluster_repo = ClusterRepository(session)

        # Get unclustered articles
        unclustered_articles = article_repo.get_recent_unclustered(hours=24)

        if not unclustered_articles:
            logger.info("No unclustered articles found")
            return

        logger.info(f"Processing {len(unclustered_articles)} unclustered articles")

        # Convert to format expected by clustering
        articles_raw = []
        for article in unclustered_articles:
            articles_raw.append({
                'id': article.id,
                'source': article.source.url if article.source else '',
                'headline': article.headline,
                'description': article.description,
                'published_at': article.published_at,
                'article_url': article.article_url,
                'image_url': article.image_url
            })

        # Preprocess and cluster
        processed_articles = preprocess_articles(articles_raw)
        if not processed_articles:
            logger.warning("No processable articles after preprocessing")
            return

        clustered_events = cluster_articles(processed_articles)

        # Save clusters to database
        for cluster in clustered_events:
            earliest_article = cluster['articles'][0]

            # Create cluster
            db_cluster = cluster_repo.create_cluster(
                title=earliest_article.get('headline', f'Event Cluster'),
                number_of_sources=len(cluster['sources_set']),
                published_at=earliest_article['published_at']
            )

            # Add articles to cluster
            for article in cluster['articles']:
                similarity_score = article.get('similarity_score', 0.0)
                db_cluster.add_article(session, article_repo.get_by_id(article['id']), similarity_score)

            # Calculate and update blindspot metrics
            session.flush()
            cluster_repo.update_cluster_blindspot(db_cluster.id)

        session.commit()
        logger.info(f"Clustering complete: {len(clustered_events)} clusters created")

def update_trending():
    """Update trending status for recent clusters"""
    logger.info("Updating trending topics...")
    
    with get_session() as session:
        cluster_repo = ClusterRepository(session)
        
        # Get recent clusters to check for trending status (last 48 hours)
        # We'll use a slightly larger window than the repo method to be safe
        from datetime import timedelta
        cutoff = now() - timedelta(hours=48)
        
        recent_clusters = session.query(Cluster).filter(
            Cluster.published_at >= cutoff.isoformat()
        ).all()
        
        count = 0
        for cluster in recent_clusters:
            if cluster_repo.calculate_trending(cluster.id):
                count += 1
        
        session.commit()
        logger.info(f"Trending updates complete. Checked {len(recent_clusters)} clusters.")

def send_pipeline_completion_notification():
    """Send notification about successful pipeline completion via API"""
    if not REQUESTS_AVAILABLE:
        logger.info("Requests not available, skipping pipeline completion notification")
        return

    try:
        # Get API base URL from environment or default
        api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')

        notification_data = {
            "title": "تحديث الأخبار",
            "body": "تم تحديث الأخبار بنجاح - Pipeline completed successfully"
        }

        response = requests.post(
            f"{api_base_url}/api/send_notification",
            json=notification_data,
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Pipeline completion notification sent: {result}")
        else:
            logger.warning(f"Failed to send notification: HTTP {response.status_code} - {response.text}")

    except Exception as e:
        logger.warning(f"Failed to send pipeline completion notification: {e}")

def run_full_pipeline():
    """Run the complete pipeline: aggregate → cluster"""
    logger.info("Starting full pipeline run")

    try:
        with pipeline_lock():
            aggregate_news()
            cluster_news()
            update_trending()
            send_pipeline_completion_notification()
            logger.info("Full pipeline run completed successfully")
    except RuntimeError as e:
        logger.error(f"Pipeline run failed: {e}")
        sys.exit(1)

def backfill_news(days):
    """Backfill news from the last N days"""
    logger.info(f"Starting backfill for last {days} days")

    try:
        with pipeline_lock():
            # For backfill, we might want to adjust the time window
            # This is a simplified version - in production you'd want more sophisticated backfill logic
            aggregate_news()
            cluster_news()
            logger.info(f"Backfill for {days} days completed")
    except RuntimeError as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Sudan News Pipeline CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # run-once command
    subparsers.add_parser('run-once', help='Run full pipeline (aggregate + cluster)')

    # aggregate-only command
    subparsers.add_parser('aggregate-only', help='Run only news aggregation')

    # cluster-only command
    subparsers.add_parser('cluster-only', help='Run only event clustering')

    # backfill command
    backfill_parser = subparsers.add_parser('backfill', help='Backfill news from last N days')
    backfill_parser.add_argument('--days', type=int, default=7, help='Number of days to backfill')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'run-once':
        run_full_pipeline()
    elif args.command == 'aggregate-only':
        try:
            with pipeline_lock():
                aggregate_news()
        except RuntimeError as e:
            logger.error(f"Aggregation failed: {e}")
            sys.exit(1)
    elif args.command == 'cluster-only':
        try:
            with pipeline_lock():
                cluster_news()
        except RuntimeError as e:
            logger.error(f"Clustering failed: {e}")
            sys.exit(1)
    elif args.command == 'backfill':
        backfill_news(args.days)

if __name__ == '__main__':
    main()
