import requests
import xml.etree.ElementTree as ET
import json
import re
from dateutil import parser
from bs4 import BeautifulSoup
from datetime import datetime
from .nlp_pipeline import analyze_text

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent)) # Also keep pipeline root for config

import config
import logging

# Import repositories
from shared_models.db import get_session
from shared_models.repositories.source_repository import SourceRepository
from shared_models.repositories.article_repository import ArticleRepository
from shared_models.repositories.entity_repository import EntityRepository

logger = logging.getLogger(__name__)

def normalize_arabic(text):
    """Normalize Arabic text by removing diacritics and standardizing characters."""
    # Remove diacritics (Tashkeel)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Convert أ,إ,آ to ا
    text = re.sub(r'[أإآ]', 'ا', text)
    # Convert ة to ه
    text = re.sub(r'ة', 'ه', text)
    # Convert ى to ي
    text = re.sub(r'ى', 'ي', text)
    return text

def parse_feed(feed_url, source_name):
    """
    Fetches and parses an XML feed from a given URL.

    Args:
        feed_url (str): The URL of the RSS feed.
        source_name (str): The source name/URL to be included in the output.

    Returns:
        list: A list of dictionaries, each representing a parsed article,
              or an empty list if an error occurs.
    """
    headers = {'User-Agent': 'Python RSS Scraper/1.0'}
    articles = []
    
    try:
        response = requests.get(feed_url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()

        # Strip leading whitespace/bytes from the content to prevent parsing errors
        xml_content = response.content.strip()
        
        root = ET.fromstring(xml_content)
        
        for item in root.findall('./channel/item'):
            headline = item.find('title').text if item.find('title') is not None else "N/A"
            description_html = item.find('description').text if item.find('description') is not None else ""
            pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
            article_url = item.find('link').text if item.find('link') is not None else "N/A"
            
            # Extract image URL, trying multiple common methods
            image_url = "N/A"
            
            # Method 1: Check for media:content tag (used by CNN, etc.)
            media_content = item.find('{http://search.yahoo.com/mrss/}content')
            if media_content is not None and media_content.get('url'):
                image_url = media_content.get('url')
            
            # Method 2: If not found, parse HTML from content:encoded or description tags
            if image_url == "N/A":
                # Prioritize the content:encoded tag as it's often more complete
                content_encoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                html_to_parse = ""
                if content_encoded is not None and content_encoded.text:
                    html_to_parse = content_encoded.text
                elif description_html:
                    html_to_parse = description_html
                
                if html_to_parse:
                    soup_for_image = BeautifulSoup(html_to_parse, 'html.parser')
                    img_tag = soup_for_image.find('img')
                    if img_tag and img_tag.get('src'):
                        image_url = img_tag.get('src')

            # Clean HTML from description
            soup = BeautifulSoup(description_html, 'html.parser')
            description_text = soup.get_text(strip=True)

            # Standardize date format to 'YYYY-MM-DD HH:MM:SS'
            standardized_date = "N/A"
            if pub_date_str:
                try:
                    parsed_date = parser.parse(pub_date_str)
                    standardized_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except parser.ParserError:
                    logger.warning(f"Could not parse date '{pub_date_str}' from {source_name}")

            article_obj = {
                "source": source_name,
                "headline": headline,
                "description": description_text,
                "published_at": standardized_date,
                "article_url": article_url,
                "image_url": image_url
            }
            articles.append(article_obj)
        
        logger.info(f"Successfully parsed {len(articles)} articles from {source_name}")
        return articles

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from {feed_url}: {e}")
    except ET.ParseError as e:
        logger.error(f"Error parsing XML from {feed_url}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred with {feed_url}: {e}")
    
    return []

def is_sudan_related(text, source_url):
    """
    Determine if text is Sudan-related using tiered keyword scoring.
    Strict filtering for international sources, permissive for local sources.
    """
    # Normalize Arabic text
    text = normalize_arabic(text.lower())

    # Check for strong keywords (immediate accept)
    for keyword in config.TIER_A_STRONG:
        normalized_kw = normalize_arabic(keyword.lower())
        if normalized_kw in text:
            return True

    # Calculate score from context and weak keywords
    score = 0

    # Tier B: Context keywords (2 points each)
    for keyword in config.TIER_B_CONTEXT:
        normalized_kw = normalize_arabic(keyword.lower())
        if normalized_kw in text:
            score += 2

    # Tier C: Weak regional keywords (1 point each)
    for keyword in config.TIER_C_WEAK:
        normalized_kw = normalize_arabic(keyword.lower())
        if normalized_kw in text:
            score += 1

    # Determine if source is international
    is_international = source_url in config.INTERNATIONAL_SOURCES

    # Apply different thresholds based on source type
    if is_international:
        # Strict: need strong keyword OR score >= 3
        return score >= 3
    else:
        # Permissive for local sources: score >= 1
        return score >= 1

if __name__ == '__main__':
    # Simple test run if executed directly
    logging.basicConfig(level=logging.INFO)
    
    total_articles = 0

    with get_session() as session:
        source_repo = SourceRepository(session)
        article_repo = ArticleRepository(session)
        entity_repo = EntityRepository(session)

        for feed in config.FEEDS:
            source_url = feed['source']
            # Determine category
            category = 'international' if source_url in config.INTERNATIONAL_SOURCES else 'local'

            # Get or create source
            source = source_repo.get_or_create_source(source_url, source_url)

            parsed_articles = parse_feed(feed['url'], feed['source'])
            inserted_count = 0
            for article_data in parsed_articles:
                if category == 'local' or (category == 'international' and is_sudan_related(article_data['headline'] + ' ' + article_data['description'], source_url)):
                    published_at = article_data['published_at'] if article_data['published_at'] != "N/A" else None

                    # Insert article using repository
                    article = article_repo.insert_article(
                        source_id=source.id,
                        headline=article_data['headline'],
                        description=article_data['description'],
                        published_at=published_at,
                        article_url=article_data['article_url'],
                        image_url=article_data['image_url'],
                        category=category
                    )

                    # Analyze text with NLP pipeline
                    text_to_analyze = article_data['headline'] + " " + article_data['description']
                    entities_json = analyze_text(text_to_analyze)
                    entities_result = json.loads(entities_json)

                    # Store entities using repository
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

        # Commit all changes
        session.commit()

    if total_articles > 0:
        logger.info(f"Total of {total_articles} articles saved to database")
    else:
        logger.info("No articles were parsed from any feed.")
