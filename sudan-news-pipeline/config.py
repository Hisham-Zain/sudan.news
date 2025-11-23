import os
import platform
from dotenv import load_dotenv

if platform.system() == 'Windows':
    load_dotenv()
else:
    # On Ubuntu, load from shared/.env relative to project root
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'shared', '.env'))

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///news_aggregator.db')

# API Keys
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
HF_TOKEN = os.getenv('HF_TOKEN')

# Model Configuration
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'google/embeddinggemma-300m')
NLP_MODEL = os.getenv('NLP_MODEL', 'gemma-3-27b-it')

# Clustering Parameters
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.5'))
TIME_WINDOW_HOURS = int(os.getenv('TIME_WINDOW_HOURS', '72'))
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

TIER_B_CONTEXT = [
    "اشتباكات", "قصف", "معارك", "نزاع", "نزاعات", "معركة", "غارات", "إطلاق نار", "تفجيرات",
    "ضحايا", "نازحين", "لاجئين", "اغتيال", "كمين", "وقف إطلاق النار", "هدنة", "مفاوضات",
    "محادثات سلام", "وساطة", "اتفاق سلام", "انتهاكات", "جرائم حرب", "جرائم ضد الإنسانية",
    "اغتصاب", "نهب", "تدمير", "احتلال", "سيطرة", "انسحاب", "تعبئة عامة",
    "القيادة العامة", "وزارة الدفاع", "مطار الخرطوم", "المطار", "سلاح الجو", "المدفعية",
    "الفرقة", "اللواء", "قوات خاصة",
    "الأمم المتحدة", "مجلس الأمن", "بعثة الأمم المتحدة", "اليونيتامس", "الاتحاد الأفريقي",
    "جامعة الدول العربية", "منظمة أطباء بلا حدود", "برنامج الغذاء العالمي",
    "الوضع الإنساني في السودان", "اللاجئين السودانيين",
    "قوى الحرية والتغيير", "المدنيين", "المجلس السيادي", "الانتقال الديمقراطي",
    "الحكومة الانتقالية", "الحكم العسكري", "الانقلاب", "الثورة السودانية", "اعتصام القيادة",
    "عبد الله حمدوك", "حقوق الإنسان", "منظمات المجتمع المدني"
]

TIER_C_WEAK = [
    "تشاد", "جنوب السودان", "إثيوبيا", "إريتريا", "مصر", "ليبيا", "أفريقيا الوسطى",
    "دول الجوار", "اللاجئين في تشاد", "الوضع الإقليمي"
]

# Scheduler settings
SCHEDULER_INTERVAL_HOURS = int(os.getenv('SCHEDULER_INTERVAL_HOURS', '6'))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'pipeline.log')

# Lock file for preventing concurrent runs
LOCK_FILE = os.getenv('LOCK_FILE', 'pipeline.lock')
