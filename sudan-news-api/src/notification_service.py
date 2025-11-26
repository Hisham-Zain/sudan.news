"""
Firebase Cloud Messaging (FCM) Notification Service

Handles push notifications for the Sudan News API.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

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
            # Check if already initialized
            if firebase_admin._apps:
                self._initialized = True
                logger.info("Firebase already initialized")
                return

            # Get credentials path from environment
            credentials_path = self._get_credentials_path()

            if not credentials_path or not os.path.exists(credentials_path):
                logger.warning(f"Firebase credentials not found at {credentials_path}")
                return

            # Initialize Firebase
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)

            self._initialized = True
            logger.info("Firebase initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self._initialized = False

    def _get_credentials_path(self) -> Optional[str]:
        """Get Firebase credentials path based on platform"""
        # Check environment variable first
        path = os.getenv('FIREBASE_CREDENTIALS_PATH')

        if path:
            return path

        # Fallback to platform-specific defaults
        import platform
        if platform.system() == 'Windows':
            return r'C:\Users\DELL\Desktop\GN\Sudan-new-Backend\firebase_key.json'
        else:
            return '/var/www/sudanese_news/shared/firebase_key.json'

    def _is_initialized(self) -> bool:
        """Check if Firebase is properly initialized"""
        return self._initialized and firebase_admin._apps

    def send_to_all_users(self, title: str, body: str, data: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Send notification to all registered users

        Args:
            title: Notification title
            body: Notification body
            data: Additional data to include

        Returns:
            Dict with success/failure counts
        """
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

            # Send to all tokens
            success_count = 0
            failure_count = 0

            for token_info in tokens:
                try:
                    self._send_single_notification(token_info['token'], title, body, data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to token {token_info['token'][:20]}...: {e}")
                    failure_count += 1

            logger.info(f"Notification sent to {success_count} users, {failure_count} failures")
            return {'success': success_count, 'failure': failure_count}

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
            return {'success': 0, 'failure': 0, 'error': str(e)}

    def send_new_cluster_notification(self, cluster_id: int) -> Dict[str, Any]:
        """
        Send notification for a new cluster

        Args:
            cluster_id: ID of the new cluster

        Returns:
            Dict with notification results
        """
        try:
            with get_session() as session:
                cluster_repo = ClusterRepository(session)
                cluster = cluster_repo.get_cluster_details(cluster_id)

            if not cluster:
                return {'error': f'Cluster {cluster_id} not found'}

            # Create notification content
            title = "خبر جديد"
            body = f"تم نشر مجموعة أخبار جديدة: {cluster['title'][:50]}..."

            data = {
                'clusterId': str(cluster_id),
                'type': 'new_cluster'
            }

            return self.send_to_all_users(title, body, data)

        except Exception as e:
            logger.error(f"Error sending new cluster notification: {e}")
            return {'error': str(e)}

    def send_popular_cluster_notification(self, cluster_id: int) -> Dict[str, Any]:
        """
        Send notification for a cluster with many sources

        Args:
            cluster_id: ID of the popular cluster

        Returns:
            Dict with notification results
        """
        try:
            with get_session() as session:
                cluster_repo = ClusterRepository(session)
                cluster = cluster_repo.get_cluster_details(cluster_id)

            if not cluster:
                return {'error': f'Cluster {cluster_id} not found'}

            source_count = cluster.get('number_of_sources', 0)
            title = "أهم الأخبار"
            body = f"مجموعة أخبار تغطيها {source_count} مصدر: {cluster['title'][:40]}..."

            data = {
                'clusterId': str(cluster_id),
                'type': 'popular_cluster',
                'sourceCount': str(source_count)
            }

            return self.send_to_all_users(title, body, data)

        except Exception as e:
            logger.error(f"Error sending popular cluster notification: {e}")
            return {'error': str(e)}

    def get_popular_clusters_for_notification(self, threshold: int = None) -> List[Dict[str, Any]]:
        """
        Get clusters that should trigger popular notifications

        Args:
            threshold: Minimum number of sources (default from env)

        Returns:
            List of cluster dicts
        """
        if threshold is None:
            threshold = int(os.getenv('NOTIFICATION_SOURCE_THRESHOLD', '10'))

        try:
            with get_session() as session:
                cluster_repo = ClusterRepository(session)
                # Get recent clusters and filter by source count
                clusters = cluster_repo.get_recent_clusters(limit=50, offset=0)

                popular_clusters = []
                for cluster in clusters:
                    if cluster.number_of_sources >= threshold:
                        popular_clusters.append({
                            'id': cluster.id,
                            'title': cluster.title,
                            'number_of_sources': cluster.number_of_sources
                        })

                return popular_clusters

        except Exception as e:
            logger.error(f"Error getting popular clusters: {e}")
            return []

    def _send_single_notification(self, token: str, title: str, body: str, data: Dict[str, str] = None):
        """
        Send notification to a single device token

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data
        """
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )

        # Send the message
        response = messaging.send(message)
        logger.debug(f"Successfully sent message: {response}")

    def cleanup_invalid_tokens(self) -> int:
        """
        Remove invalid/expired tokens based on FCM errors

        Returns:
            Number of tokens removed
        """
        # This would be implemented with proper error handling
        # For now, return 0
        logger.info("Token cleanup not yet implemented")
        return 0


# Global notification service instance
notification_service = NotificationService()
