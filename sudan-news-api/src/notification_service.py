"""
Firebase Cloud Messaging (FCM) Notification Service

Handles push notifications for the Sudan News API.
ONLY FCM is used. Expo notifications have been completely removed.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, messaging

from shared_models.repositories.token_repository import TokenRepository
from shared_models.repositories.cluster_repository import ClusterRepository
from shared_models.db import get_session

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging"""

    def __init__(self):
        self._initialized = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if firebase_admin._apps:
                self._initialized = True
                logger.info("Firebase already initialized")
                return

            credentials_path = self._get_credentials_path()

            if not credentials_path or not os.path.exists(credentials_path):
                logger.warning(f"Firebase credentials not found at {credentials_path}")
                return

            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)

            self._initialized = True
            logger.info("Firebase initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self._initialized = False

    def _get_credentials_path(self) -> Optional[str]:
        """Get Firebase credentials path based on platform"""
        path = os.getenv('FIREBASE_CREDENTIALS_PATH')
        if path:
            return path

        import platform
        if platform.system() == 'Windows':
            return r'C:\Users\DELL\Desktop\GN\Sudan-new-Backend\firebase_key.json'
        else:
            return '/var/www/sudanese_news/shared/firebase_key.json'

    def _is_initialized(self) -> bool:
        return self._initialized and firebase_admin._apps

    # ------------------------------------------------------------------
    # PUBLIC - Send to all tokens
    # ------------------------------------------------------------------
    def send_to_all_users(self, title: str, body: str, data: Dict[str, str] = None) -> Dict[str, Any]:

        if not self._is_initialized():
            logger.error("Firebase not initialized")
            return {'success': 0, 'failure': 0, 'error': 'Firebase not initialized'}

        try:
            with get_session() as session:
                token_repo = TokenRepository(session)
                tokens = token_repo.get_all_active_tokens()

            if not tokens:
                logger.info("No active tokens found")
                return {'success': 0, 'failure': 0, 'message': 'No active tokens'}

            success = 0
            failure = 0

            for t in tokens:
                token = t["token"]
                try:
                    self._send_single_fcm_notification(token, title, body, data)
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to send to {token[:20]}...: {e}")
                    failure += 1

            return {'success': success, 'failure': failure}

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
            return {'success': 0, 'failure': 0, 'error': str(e)}

    # ------------------------------------------------------------------
    # Send new cluster notification
    # ------------------------------------------------------------------
    def send_new_cluster_notification(self, cluster_id: int) -> Dict[str, Any]:
        try:
            with get_session() as session:
                repo = ClusterRepository(session)
                cluster = repo.get_cluster_details(cluster_id)

            if not cluster:
                return {'error': f'Cluster {cluster_id} not found'}

            title = "خبر جديد"
            body = f"تم نشر مجموعة أخبار جديدة: {cluster['title'][:50]}..."

            data = {"clusterId": str(cluster_id), "type": "new_cluster"}

            return self.send_to_all_users(title, body, data)

        except Exception as e:
            logger.error(f"Error sending new cluster notification: {e}")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # Get popular clusters for notification
    # ------------------------------------------------------------------
    def get_popular_clusters_for_notification(self) -> List[Dict[str, Any]]:
        """Get clusters that have 2 or more articles (considered 'popular/developing' news)"""
        try:
            with get_session() as session:
                repo = ClusterRepository(session)
                # Get recent clusters from last 48 hours
                from datetime import datetime, timedelta
                cutoff = datetime.now() - timedelta(hours=48)

                # Get recent clusters and filter those with 2+ articles
                recent_clusters = repo.get_recent_clusters(limit=100)  # Get more to filter
                popular_clusters = []

                for cluster in recent_clusters:
                    # Check if cluster was created within last 48 hours
                    try:
                        cluster_date = datetime.fromisoformat(cluster.created_at.replace('Z', '+00:00'))
                        if cluster_date < cutoff:
                            continue
                    except:
                        continue

                    # Get cluster details to check article count
                    cluster_details = repo.get_cluster_details(cluster.id)
                    if cluster_details and len(cluster_details.get('articles', [])) >= 2:
                        popular_clusters.append({
                            'id': cluster.id,
                            'title': cluster.title,
                            'number_of_sources': cluster.number_of_sources,
                            'article_count': len(cluster_details['articles']),
                            'created_at': cluster.created_at
                        })

                # Sort by article count (most articles first) and limit to top 10
                popular_clusters.sort(key=lambda x: x['article_count'], reverse=True)
                return popular_clusters[:10]

        except Exception as e:
            logger.error(f"Error getting popular clusters for notification: {e}")
            return []

    # ------------------------------------------------------------------
    # Send popular cluster notification
    # ------------------------------------------------------------------
    def send_popular_cluster_notification(self, cluster_id: int) -> Dict[str, Any]:
        try:
            with get_session() as session:
                repo = ClusterRepository(session)
                cluster = repo.get_cluster_details(cluster_id)

            if not cluster:
                return {'error': f'Cluster {cluster_id} not found'}

            articles = cluster.get('articles', [])
            if not articles:
                return {'error': f'No articles found for cluster {cluster_id}'}

            article_count = len(articles)

            # Find the earliest article by published_at date
            earliest_article = None
            earliest_date = None

            for article in articles:
                if article.get('published_at'):
                    try:
                        article_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                        if earliest_date is None or article_date < earliest_date:
                            earliest_date = article_date
                            earliest_article = article
                    except (ValueError, TypeError):
                        continue

            # Use earliest article's headline as title, fallback to cluster title
            if earliest_article:
                title = earliest_article.get('headline', cluster['title'])[:50]
                # Format the date for display
                date_str = earliest_date.strftime('%Y-%m-%d %H:%M') if earliest_date else ''
                body = f"خبر متطور: {article_count} مصادر - {date_str}"
            else:
                # Fallback to original logic if no dates available
                title = cluster['title'][:50]
                body = f"مجموعة أخبار تحتوي على {article_count} مقالة"

            data = {
                "clusterId": str(cluster_id),
                "type": "popular_cluster",
                "articleCount": str(article_count)
            }

            return self.send_to_all_users(title, body, data)

        except Exception as e:
            logger.error(f"Error sending popular cluster notification: {e}")
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # INTERNAL - FCM ONLY (Expo removed)
    # ------------------------------------------------------------------
    def _send_single_fcm_notification(self, token: str, title: str, body: str, data: Dict[str, str] = None):
        """
        Sends a SINGLE FCM notification.
        This is the only notification method that remains.
        """

        # Ensure we always send a proper FCM notification payload:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="default",
                )
            )
        )

        response = messaging.send(message)
        logger.debug(f"FCM sent: {response}")

    # ------------------------------------------------------------------
    def cleanup_invalid_tokens(self) -> int:
        logger.info("Token cleanup not implemented yet")
        return 0


# Global instance
notification_service = NotificationService()
