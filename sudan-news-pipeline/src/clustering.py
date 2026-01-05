import json
import os
import re
import platform
from sentence_transformers import SentenceTransformer, util
from datetime import datetime, timedelta
import numpy as np
from dotenv import load_dotenv
from huggingface_hub import login
import psutil
import torch

# Import repositories
from shared_models.db import get_session
from shared_models.repositories.article_repository import ArticleRepository
from shared_models.repositories.cluster_repository import ClusterRepository

# Import config
import config

if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from absolute path
    load_dotenv('/var/www/sudanese.news/shared/.env')

login(config.HF_TOKEN)

# Configuration - now using centralized config
MODEL_NAME = config.EMBEDDING_MODEL
SIMILARITY_THRESHOLD = config.SIMILARITY_THRESHOLD
TIME_WINDOW_HOURS = config.TIME_WINDOW_HOURS

def log_system_info():
    """Log GPU and initial memory information"""
    print("=== System Information ===")

    # GPU Detection
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        print(f"GPU Available: Yes ({gpu_count} device(s))")
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3  # GB
            print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        print("GPU Available: No")

    # Initial RAM
    memory = psutil.virtual_memory()
    print(f"Total RAM: {memory.total / 1024**3:.1f} GB")
    print(f"Available RAM: {memory.available / 1024**3:.1f} GB")
    print(f"RAM Usage: {memory.percent}%")
    print("========================\n")

def log_memory_usage(step_name):
    """Log current memory usage"""
    memory = psutil.virtual_memory()
    process = psutil.Process()
    process_memory = process.memory_info().rss / 1024**2  # MB
    print(f"[{step_name}] RAM Usage: {memory.percent:.1f}% ({memory.used / 1024**3:.1f} GB used, {memory.available / 1024**3:.1f} GB free)")
    print(f"[{step_name}] Process Memory: {process_memory:.1f} MB")

def normalize_arabic(text):
    text = re.sub('[ًٌٍَُِّْـ]', '', text)  # remove diacritics and tatweel
    text = re.sub('[إأآا]', 'ا', text)     # unify alef
    text = re.sub('ة', 'ه', text)          # unify taa marbuta
    text = re.sub('ى', 'ي', text)          # unify alif maqsoora
    return text

def preprocess_articles(articles):
    """
    Loads articles, parses dates, and generates embeddings.
    Handles potential errors in date parsing gracefully.
    """
    model = SentenceTransformer(MODEL_NAME)
    processed_articles = []

    for article in articles:
        # Normalize Arabic text in headline and description
        normalized_headline = normalize_arabic(article.get('headline', ''))
        normalized_description = normalize_arabic(article.get('description', ''))

        # Combine headline and description for richer semantic content
        content = f"{normalized_headline}. {normalized_description}"
        if not content.strip() or content.strip() == '.':
            continue # Skip articles with no content

        # Generate embedding
        article['embedding'] = model.encode(content, convert_to_tensor=True)

        # Parse publication date
        try:
            # Attempt to parse multiple potential date formats
            article['published_dt'] = datetime.strptime(article['published_at'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            # If parsing fails or date is missing, skip the article
            # as it cannot be used in time-based clustering.
            print(f"Warning: Could not parse date for article: {article.get('headline')}. Skipping.")
            continue

        processed_articles.append(article)

    # Sort articles by publication date to process them chronologically
    processed_articles.sort(key=lambda x: x['published_dt'])
    return processed_articles


def cluster_articles(articles):
    """
    Clusters articles into events based on time, semantic similarity, and source uniqueness.
    """
    clusters = []

    for article in articles:
        best_match_cluster = None
        highest_similarity = -1.0 # Initialize to a value lower than any possible similarity score

        active_clusters = [
            c for c in clusters
            if (article['published_dt'] - c['last_updated']) <= timedelta(hours=TIME_WINDOW_HOURS)
        ]

        # Find the best matching cluster among active ones
        for cluster in active_clusters:
            # Check if the source is already in the cluster
            if article['source'] in cluster['sources_set']:
                continue

            # Calculate similarity
            similarity = util.pytorch_cos_sim(article['embedding'], cluster['representative_vector'])[0][0].item()

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match_cluster = cluster

        # Decision and Assignment
        if highest_similarity > SIMILARITY_THRESHOLD and best_match_cluster:
            # Assign to existing cluster
            article['similarity_score'] = highest_similarity
            best_match_cluster['articles'].append(article)
            best_match_cluster['sources_set'].add(article['source'])
            best_match_cluster['last_updated'] = article['published_dt']
            # Re-calculate representative vector (simple average)
            all_embeddings = [art['embedding'] for art in best_match_cluster['articles']]
            best_match_cluster['representative_vector'] = np.mean([emb.cpu().numpy() for emb in all_embeddings], axis=0)

        else:
            # Create a new cluster
            article['similarity_score'] = 1.0  # Similarity to itself for the first article
            clusters.append({
                'articles': [article],
                'sources_set': {article['source']},
                'representative_vector': article['embedding'],
                'created_at': article['published_dt'],
                'last_updated': article['published_dt']
            })

    return clusters



def main():
    """
    Main function to run the clustering process.
    """
    # Log system information
    log_system_info()

    with get_session() as session:
        article_repo = ArticleRepository(session)
        cluster_repo = ClusterRepository(session)

        # Get recent unclustered articles using repository
        articles_raw = article_repo.get_recent_unclustered(hours=168)  # Last 7 days

        if not articles_raw:
            print("No unclustered articles found in database. Exiting.")
            return

        # Convert Article objects to dictionaries for processing
        articles_list = []
        for article in articles_raw:
            articles_list.append({
                'id': article.id,
                'source': article.source.url if article.source else '',
                'headline': article.headline,
                'description': article.description or '',
                'published_at': article.published_at,
                'article_url': article.article_url,
                'image_url': article.image_url
            })

        # 1. Pre-process articles (generate embeddings, parse dates)
        print("Step 1: Pre-processing articles and generating embeddings...")
        log_memory_usage("Before Preprocessing")
        processed_articles = preprocess_articles(articles_list)
        log_memory_usage("After Preprocessing")
        if not processed_articles:
            print("No processable articles found. Exiting.")
            return

        # 2. Cluster the articles
        print("Step 2: Clustering articles into events...")
        log_memory_usage("Before Clustering")
        clustered_events = cluster_articles(processed_articles)
        log_memory_usage("After Clustering")

        # 3. Save clusters to database using repositories
        print("Step 3: Saving clusters to database...")
        for cluster_data in clustered_events:
            earliest_article = cluster_data['articles'][0]
            title = earliest_article.get('headline', 'Event Cluster')
            number_of_sources = len(cluster_data['sources_set'])
            published_at = earliest_article['published_at']

            # Create cluster using repository
            cluster = cluster_repo.create_cluster(title, number_of_sources, published_at)

            # Add articles to cluster
            for article_data in cluster_data['articles']:
                similarity_score = article_data.get('similarity_score', 0.0)
                # Note: The Cluster.add_article method would need to be implemented
                # For now, we'll use raw SQL for the many-to-many relationship
                from shared_models.models import cluster_articles
                from sqlalchemy import insert
                stmt = insert(cluster_articles).values(
                    cluster_id=cluster.id,
                    article_id=article_data['id'],
                    similarity_score=float(similarity_score)
                )
                session.execute(stmt)
            
            # Calculate and update blindspot metrics
            session.flush()  # Ensure articles are linked before calculation
            cluster_repo.update_cluster_blindspot(cluster.id)

        session.commit()
        print(f"Clustering complete. Saved {len(clustered_events)} clusters to database.")


if __name__ == "__main__":
    main()
