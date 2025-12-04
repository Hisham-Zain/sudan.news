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
from shared_models.timezone_utils import to_app_timezone

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

            # Standardize date format to 'YYYY-MM-DD HH:MM:SS' in app timezone
            standardized_date = "N/A"
            if pub_date_str:
                try:
                    parsed_date = parser.parse(pub_date_str)
                    # Convert to app timezone and format
                    app_timezone_date = to_app_timezone(parsed_date)
                    standardized_date = app_timezone_date.strftime('%Y-%m-%d %H:%M:%S')
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

def normalize_text(text):
    """Normalize text by removing punctuation and converting to lowercase."""
    import re
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower()

def is_sudan_related(article, source_type='international'):
    """
    Determine if article is Sudan-related using zone weighting + exclusion filtering.
    article: dict containing 'headline', 'description'
    source_type: 'international' or 'local'
    """
    # 1. Prepare Text Zones
    title_text = normalize_text(article.get('headline', ''))
    body_text = normalize_text(article.get('description', ''))
    full_text = title_text + " " + body_text

    # If local, keep permissive logic
    if source_type == 'local':
        # Simple check: any Sudan-related keyword in title or body
        for kw in config.TIER_A_DEFINITIVE + config.TIER_A_STRONG:
            if normalize_arabic(kw.lower()) in full_text or kw.lower() in full_text:
                return True
        return len([kw for kw in config.TIER_B_CONTEXT if normalize_arabic(kw.lower()) in full_text]) >= 1

    # --- INTERNATIONAL LOGIC ---

    # 2. The Exclusion Check (Negative Filtering)
    # Check if the article is clearly about a different major conflict
    has_exclusion_word = any(kw.lower() in title_text for kw in config.EXCLUSION_KEYWORDS)

    # 3. Definitive Check (The "Golden Ticket")
    # If a definitive keyword is in the TITLE, accept immediately.
    for kw in config.TIER_A_DEFINITIVE:
        if normalize_arabic(kw.lower()) in title_text or kw.lower() in title_text:
            return True

    # If a definitive keyword is in the BODY, accept (unless it's an excluded topic)
    tier_a_in_body = any(
        normalize_arabic(kw.lower()) in body_text or kw.lower() in body_text
        for kw in config.TIER_A_DEFINITIVE
    )

    if tier_a_in_body and not has_exclusion_word:
        return True

    # If it has an exclusion word (e.g., Gaza), it MUST have "Sudan" explicitly in the title
    # to pass. Since we failed the "Tier A in Title" check above, we reject here.
    if has_exclusion_word:
        return False

    # 4. Contextual Scoring (Only if no definitive match found yet)
    score = 0

    # Weight Title matches x3
    for kw in config.TIER_B_CONTEXT:
        norm_kw = normalize_arabic(kw.lower())
        if norm_kw in title_text:
            score += 3
        elif norm_kw in body_text:
            score += 1

    # 5. Thresholds
    # If we have no Tier A keywords, we need a very high context score
    # implying the article talks about "Army" + "Clashes" + "Jeddah" + "Negotiations"
    if score >= 4:
        return True

    return False

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
                if is_sudan_related(article_data, category):
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
