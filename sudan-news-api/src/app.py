#!/usr/bin/env python3
"""
Sudan News API - Consumer Service

Flask application providing REST API and web interface for Sudanese news events.
This service is read-only for event data and uses the shared repository pattern.
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path for shared_models import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import shared models and repositories
from shared_models.db import get_session
from shared_models.repositories.cluster_repository import ClusterRepository
from shared_models.repositories.token_repository import TokenRepository
from shared_models.repositories.article_repository import ArticleRepository
from shared_models.repositories.source_repository import SourceRepository

# Setup Flask app
app = Flask(__name__,
            template_folder=str(Path(__file__).parent.parent / 'templates'),
            static_folder=str(Path(__file__).parent.parent / 'static'))
CORS(app)

# Bias data is now stored in the database, not in a separate JSON file
# The ClusterRepository now returns bias and other source details directly

# Jinja2 filters (same as original)
@app.template_filter('timeago_arabic')
def timeago_arabic_filter(date_string):
    """Convert date string to Arabic time ago format."""
    try:
        date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        now = datetime.now()
        seconds = int((now - date).total_seconds())

        if seconds < 60:
            return "الآن"
        elif seconds < 3600:
            minutes = seconds // 60
            if minutes == 1:
                return "منذ دقيقة"
            elif minutes == 2:
                return "منذ دقيقتين"
            else:
                return f"منذ {minutes} دقائق"
        elif seconds < 86400:
            hours = seconds // 3600
            if hours == 1:
                return "منذ ساعة"
            elif hours == 2:
                return "منذ ساعتين"
            else:
                return f"منذ {hours} ساعات"
        elif seconds < 2592000:  # 30 days
            days = seconds // 86400
            if days == 1:
                return "قبل يوم"
            elif days == 2:
                return "قبل يومين"
            else:
                return f"قبل {days} أيام"
        else:
            return date.strftime('%Y-%m-%d')
    except:
        return date_string

@app.template_filter('datetime_arabic')
def datetime_arabic_filter(date_string):
    """Convert date string to Arabic formatted datetime."""
    try:
        date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return date.strftime('%Y-%m-%d %H:%M')
    except:
        return date_string

@app.template_filter('bias_arabic')
def bias_arabic_filter(bias_value):
    """Convert English bias value to Arabic."""
    bias_mapping = {
        'Neutral': 'محايد',
        'Pro-SAF': 'مؤيد - القوات المسلحة',
        'Oppose-SAF': 'معارض - القوات المسلحة',
        'neutral': 'محايد',
        'pro-saf': 'مؤيد - القوات المسلحة',
        'oppose-saf': 'معارض - القوات المسلحة'
    }
    return bias_mapping.get(bias_value, 'غير محدد')

# Web Routes (unchanged)

@app.route('/')
def index():
    """Homepage showing recent clusters with pagination and search/filter."""
    per_page = 100  # Number of clusters per page
    page = int(request.args.get('page', 1))
    offset = (page - 1) * per_page

    q = request.args.get('q', '').strip()
    has_entities = request.args.get('has_entities', '')
    category = request.args.get('category', 'all')
    city = request.args.get('city', '')

    try:
        with get_session() as session:
            cluster_repo = ClusterRepository(session)
            
            # Get all cities for the filter dropdown
            all_cities = cluster_repo.get_all_cities()

            if q or has_entities or (category and category != 'all') or city:
                clusters, total_clusters = cluster_repo.get_clusters_with_filters(
                    query=q if q else None,
                    has_entities=has_entities == '1',
                    category=category if category != 'all' else None,
                    city=city if city else None,
                    limit=per_page,
                    offset=offset
                )
            else:
                clusters = cluster_repo.get_recent_clusters(per_page, offset)
                total_clusters = cluster_repo.get_total_clusters()

            # Fetch war news for sidebar (Security category)
            war_clusters, _ = cluster_repo.get_clusters_with_filters(
                category='security',
                limit=5
            )
            
            # Fetch trending clusters
            trending_clusters = cluster_repo.get_trending_clusters(limit=5)
            
            # Detach trending clusters from session to use outside
            session.expunge_all()
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('error.html', error="An error occurred while loading the page."), 500

    total_pages = (total_clusters + per_page - 1) // per_page  # Ceiling division

    # Calculate page numbers to display (current page +/- 2)
    start_page = max(1, page - 2)
    end_page = min(total_pages + 1, page + 3)
    page_numbers = list(range(start_page, end_page))

    # Helper to enrich clusters with article data
    def enrich_clusters(cluster_list):
        for cluster in cluster_list:
            with get_session() as session:
                cluster_repo = ClusterRepository(session)
                cluster_data = cluster_repo.get_cluster_details(cluster.id)

                if cluster_data and cluster_data['articles']:
                    # Add first article to cluster for template rendering
                    setattr(cluster, 'first_article', cluster_data['articles'][0])
                    
                    # Add bias distribution data if available
                    if cluster_data.get('bias_distribution'):
                        setattr(cluster, 'bias_distribution', cluster_data['bias_distribution'])
                    
                    # Use NLP categories for labeling if available
                    nlp_categories = []
                    for article in cluster_data['articles']:
                        if article.get('nlp_category'):
                            nlp_categories.append(article['nlp_category'])
                    if nlp_categories:
                        # Use the first NLP category as label
                        setattr(cluster, 'category_label', nlp_categories[0])
                else:
                    # Fallback to local/international
                    # Note: cluster_data might be None if cluster deleted but still in list? Unlikely but possible.
                    if cluster_data and cluster_data.get('articles'):
                        categories = set(article['category'] for article in cluster_data['articles'])
                        if 'local' in categories and 'international' in categories:
                            setattr(cluster, 'category_label', 'محلي ودولي')
                        elif 'international' in categories:
                            setattr(cluster, 'category_label', 'دولي')
                        else:
                            setattr(cluster, 'category_label', 'محلي')

    # Enrich both lists
    enrich_clusters(clusters)
    enrich_clusters(trending_clusters)

    return render_template('index.html', clusters=clusters, page=page, total_pages=total_pages, page_numbers=page_numbers, all_cities=all_cities, current_city=city, war_clusters=war_clusters, trending_clusters=trending_clusters)

@app.route('/event/<int:cluster_id>')
def event(cluster_id):
    """Show details of a specific cluster."""
    try:
        with get_session() as session:
            cluster_repo = ClusterRepository(session)
            cluster = cluster_repo.get_cluster_details(cluster_id)
    except Exception as e:
        logger.error(f"Error in event route for id {cluster_id}: {e}")
        return render_template('error.html', error="An error occurred while loading the event."), 500

    if cluster:
        # Bias is now included in the article data from the repository
        pass

    return render_template('event.html', cluster=cluster)

@app.route('/source/<int:source_id>')
def source(source_id):
    """Show details of a specific news source."""
    try:
        with get_session() as session:
            source_repo = SourceRepository(session)
            source = source_repo.get_source_details(source_id)
    except Exception as e:
        logger.error(f"Error in source route for id {source_id}: {e}")
        return render_template('error.html', error="An error occurred while loading the source."), 500

    if not source:
        return render_template('error.html', error="المصدر غير موجود"), 404

    return render_template('source.html', source=source)

# API Routes (maintaining exact same responses)

@app.route('/api/clusters')
def api_clusters():
    """API endpoint for recent clusters formatted for mobile app."""
    per_page = int(request.args.get('limit', 50))
    page = int(request.args.get('page', 1))
    offset = (page - 1) * per_page

    q = request.args.get('q', '').strip()
    has_entities = request.args.get('has_entities', '')
    category = request.args.get('category', 'all')
    city = request.args.get('city', '')

    try:
        with get_session() as session:
            cluster_repo = ClusterRepository(session)

            if q or has_entities or (category and category != 'all') or city:
                clusters, _ = cluster_repo.get_clusters_with_filters(
                    query=q if q else None,
                    has_entities=has_entities == '1',
                    category=category if category != 'all' else None,
                    city=city if city else None,
                    limit=per_page,
                    offset=offset
                )
            else:
                clusters = cluster_repo.get_recent_clusters(per_page, offset)
    except Exception as e:
        logger.error(f"Error in api_clusters: {e}")
        return jsonify({'error': 'Internal server error'}), 500

    # Format for mobile API (maintain exact same structure)
    result = []
    for cluster in clusters:
        with get_session() as session:
            cluster_repo = ClusterRepository(session)
            cluster_data = cluster_repo.get_cluster_details(cluster.id)

            if not cluster_data or not cluster_data['articles']:
                continue

            articles = cluster_data['articles']

            # headline: cluster title
            headline = cluster.title

            # description: first article's description
            description = articles[0]['description'] if articles else ''

            # image_url: first article's image_url
            image_url = articles[0]['image_url'] if articles else ''

            # first_date_of_publication: min published_at
            dates = []
            for a in articles:
                if a['published_at']:
                    try:
                        dates.append(datetime.fromisoformat(a['published_at'].replace('Z','+00:00')))
                    except:
                        pass
            first_date = min(dates) if dates else None
            first_date_str = first_date.isoformat() if first_date else ''

            # number_of_sources: already there
            number_of_sources = cluster.number_of_sources

            # country/city: collect unique cities and countries
            cities = set()
            countries = set()
            for article in articles:
                if article.get('entities'):
                    cities.update(article['entities'].get('cities', []))
                    countries.update(article['entities'].get('countries', []))

            # format as "Country/City"
            location = ''
            if countries and cities:
                location = f"{list(countries)[0]}/{list(cities)[0]}"
            elif countries:
                location = list(countries)[0]
            elif cities:
                location = list(cities)[0]

            result.append({
                'id': cluster.id,
                'headline': headline,
                'description': description,
                'image_url': image_url,
                'country_city': location,
                'first_date_of_publication': first_date_str,
                'number_of_sources': number_of_sources,
                'bias_distribution': cluster_data.get('bias_distribution'),
                'is_trending': cluster.is_trending
            })

    # Add caching headers
    response = jsonify(result)
    response.headers['Cache-Control'] = 'max-age=300'  # 5 minutes
    return response

@app.route('/api/cluster/<int:cluster_id>')
def api_cluster(cluster_id):
    """API endpoint for cluster details."""
    with get_session() as session:
        cluster_repo = ClusterRepository(session)
        cluster = cluster_repo.get_cluster_details(cluster_id)

    if cluster:
        # Bias and other source details are now included in the article data from the repository
        response = jsonify(cluster)
        response.headers['Cache-Control'] = 'max-age=600'  # 10 minutes
        return response

    return jsonify({'error': 'Cluster not found'}), 404

@app.route('/api/categories')
def api_categories():
    """API endpoint for unique categories from entities."""
    with get_session() as session:
        cluster_repo = ClusterRepository(session)
        # Get categories from cluster filtering (this approximates the original logic)
        _, _ = cluster_repo.get_clusters_with_filters(limit=1, offset=0)
        # For now, return static categories (can be enhanced later)
        categories = ['سياسة', 'أمن وعسكر', 'اقتصاد', 'رياضة', 'مجتمع وثقافة', 'مقالات رأي']

    response = jsonify(categories)
    response.headers['Cache-Control'] = 'max-age=3600'  # 1 hour
    return response

@app.route('/api/cities')
def api_cities():
    """API endpoint for unique cities from entities."""
    with get_session() as session:
        cluster_repo = ClusterRepository(session)
        cities = cluster_repo.get_all_cities()

    response = jsonify(cities)
    response.headers['Cache-Control'] = 'max-age=3600'  # 1 hour
    return response

@app.route('/api/articles')
def api_articles():
    """API endpoint for articles with filtering."""
    filters = {}
    if request.args.get('date_from'):
        filters['date_from'] = request.args.get('date_from')
    if request.args.get('date_to'):
        filters['date_to'] = request.args.get('date_to')
    if request.args.get('keyword'):
        filters['keyword'] = request.args.get('keyword')

    with get_session() as session:
        article_repo = ArticleRepository(session)
        articles = article_repo.list_by_filters(filters, limit=100)

    response = jsonify(articles)
    response.headers['Cache-Control'] = 'max-age=300'  # 5 minutes
    return response

@app.route('/api/register_token', methods=['POST'])
def api_register_token():
    """API endpoint to register push notification tokens."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user_id = data.get('user_id')
    device_id = data.get('device_id')
    token = data.get('token')
    platform = data.get('platform')

    if not all([device_id, token, platform]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        with get_session() as session:
            token_repo = TokenRepository(session)
            token_repo.store_or_update_token(user_id, device_id, token, platform)
            session.commit()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return jsonify({'status': 'healthy', 'service': 'sudan-news-api'})

if __name__ == '__main__':
    # Run Flask app (no scheduler - that's in the pipeline now)
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
