import os
import platform
from dotenv import load_dotenv

if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from absolute path
    load_dotenv('/var/www/sudanese_news/shared/.env')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///news_aggregator.db')

# API Keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # Backward compatibility
GOOGLE_API_KEYS = [
    os.getenv('GOOGLE_API_KEY_1', os.getenv('GOOGLE_API_KEY')),  # Fallback to single key
    os.getenv('GOOGLE_API_KEY_2'),
    os.getenv('GOOGLE_API_KEY_3'),
    os.getenv('GOOGLE_API_KEY_4')
]
# Filter out None values
GOOGLE_API_KEYS = [key for key in GOOGLE_API_KEYS if key is not None]

HF_TOKEN = os.getenv('HF_TOKEN')

# Model Configuration
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'google/embeddinggemma-300m')
NLP_MODEL = os.getenv('NLP_MODEL', 'gemma-3-27b-it')

# Clustering Parameters
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.5'))
TIME_WINDOW_HOURS = int(os.getenv('TIME_WINDOW_HOURS', '300'))
MAX_ARTICLES_PER_CLUSTER = int(os.getenv('MAX_ARTICLES_PER_CLUSTER', '50'))

# Pipeline Settings
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))

# RSS Feed URLs
FEEDS = [
    {"url": "https://sudanile.com/feed/", "source": "https://sudanile.com/"},
    {"url": "https://www.dabangasudan.org/ar/الاخبار/feed", "source": "https://www.dabangasudan.org/ar"},
    {"url": "https://www.radiotamazuj.org/ar/rss/news.xml", "source": "https://www.radiotamazuj.org/ar"},
    {"url": "https://www.altaghyeer.info/ar/feed/", "source": "https://www.altaghyeer.info/ar"},
    {"url": "https://suda.news/feed", "source": "https://suda.news"},
    {"url": "https://tasamuhnews.com/feed/", "source": "https://tasamuhnews.com"},
    {"url": "https://www.sudaninet.net/feed", "source": "https://www.sudaninet.net"},
    {"url": "https://www.alnilin.com/feed", "source": "https://www.alnilin.com"},
    {"url": "https://www.almashhad.news/feed", "source": "https://www.almashhad.news"},
    {"url": "https://kushnews.net/feed", "source": "https://kushnews.net"},
    {"url": "https://sudafax.com/feed", "source": "https://sudafax.com"},
    {"url": "https://www.tagpress.net/feed/", "source": "https://www.tagpress.net"},
    {"url": "https://arabic.cnn.com/api/v1/rss/rss.xml", "source": "https://arabic.cnn.com"},
    {"url": "https://sudantribune.net/feed", "source": "https://sudantribune.net"},
    {"url": "https://www.darfur24.com/feed/", "source": "https://www.darfur24.com"},
    {"url": "https://www.sudani.news/feed/", "source": "https://www.sudani.news"},
    {"url": "https://www.alsahafa.net/feed/", "source": "https://www.alsahafa.net"},
    {"url": "https://www.aljazeera.net/rss", "source": "https://www.aljazeera.net"},
    {"url": "https://www.skynewsarabia.com/rss", "source": "https://www.skynewsarabia.com"},
    {"url": "https://www.france24.com/ar/rss", "source": "https://www.france24.com"},
    {"url": "https://arabic.euronews.com/rss", "source": "https://arabic.euronews.com"},
    {"url": "https://feeds.feedburner.com/alalamfeed", "source": "https://alalam.ir"},
    {"url": "https://arabic.rt.com/rss/", "source": "https://arabic.rt.com"},
    {"url": "https://www.alsumaria.tv/Rss/News/ar/49/%D8%AF%D9%88%D9%84%D9%8A%D8%A7%D8%AA", "source": "https://www.alsumaria.tv"},
    {"url": "https://alhiwar.tv/feed/", "source": "https://alhiwar.tv"},
    {"url": "https://www.almasryalyoum.com/feed", "source": "https://www.almasryalyoum.com"},
    {"url": "https://www.elkhabar.com/feed", "source": "https://www.elkhabar.com"}
]

# International sources (for filtering)
INTERNATIONAL_SOURCES = [
    "https://arabic.cnn.com",
    "https://www.skynewsarabia.com",
    "https://aawsat.com",
    "https://www.aljazeera.net",
    "https://www.almashhad.news",
    "https://www.france24.com",
    "https://arabic.euronews.com",
    "https://alalam.ir",
    "https://arabic.rt.com",
    "https://www.alsumaria.tv",
    "https://alhiwar.tv",
    "https://www.almasryalyoum.com",
    "https://www.elkhabar.com"
]

# Keyword filtering tiers
TIER_A_STRONG = [
    "السودان", "سودان", "الخرطوم", "أمدرمان", "بحري", "دارفور", "الفاشر", "نيالا", "زالنجي",
    "الجنينة", "كردفان", "جنوب كردفان", "شمال كردفان", "النيل الأزرق", "بورسودان", "كسلا",
    "سنار", "مدني", "الجزيرة", "القضارف", "الدمازين", "دنقلا", "حلفا", "كوستي", "ربك", "أبوحمد",
    "الجيش السوداني", "القوات المسلحة السودانية", "قوات الدعم السريع", "الدعم السريع",
    "البرهان", "عبدالفتاح البرهان", "حميدتي", "محمد حمدان دقلو", "محمد حمدان", "هيثم برهان"
]

# TIER A: definitive proof (Names, unique acronyms, main cities)
# If these appear, it is almost certainly about Sudan.
TIER_A_DEFINITIVE = [
    "السودان", "الخرطوم", "أم درمان", "نيالا", "بورتسودان", "الفاشر", "الجنينة", "دارفور",
    "الدعم السريع", "البرهان", "حميدتي", "حمدوك", "القوات المسلحة السودانية",
    "مجلس السيادة السوداني", "RSF", "SAF", "Sudan", "Khartoum", "Darfur"
]

# NEGATIVE FILTER: Common international topics that cause false positives
# If these exist, we require a TIER A match to override them.
EXCLUSION_KEYWORDS = [
    "غزة", "فلسطين", "لبنان", "أوكرانيا", "روسيا", "الاحتلال",
    "Gaza", "Ukraine", "Palestine", "Israel", "Hezbollah"
]

TIER_B_CONTEXT = [
    "الجيش", "اشتباكات", "نزاع", "مفاوضات", "جنيف", "جدة",
    "الإيغاد", "النزوح", "المجاعة", "اللاجئين"
]

TIER_C_WEAK = [
    "تشاد", "جنوب السودان", "إثيوبيا", "إريتريا", "مصر", "ليبيا", "أفريقيا الوسطى",
    "دول الجوار", "اللاجئين في تشاد", "الوضع الإقليمي"
]

# Scheduler settings
SCHEDULER_INTERVAL_HOURS = int(os.getenv('SCHEDULER_INTERVAL_HOURS', '6'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', '/var/www/sudanese_news/shared/logs/pipeline.log' if platform.system() != 'Windows' else 'shared/logs/pipeline.log')

# Lock file for preventing concurrent runs
LOCK_FILE = os.getenv('LOCK_FILE', 'pipeline.lock')
