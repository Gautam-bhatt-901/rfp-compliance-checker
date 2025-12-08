"""
Configuration settings for RFP Compliance Checker - FastAPI Version
All extraction and matching logic settings
Database, auth, and CORS settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============ API SETTINGS ============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Database settings
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rfp_app.db")
DATABASE_URL = "postgresql://rfp_user:admin@localhost:5432/rfp_db"

# ============   Directory Configuration ============
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / 'data'
UPLOAD_RFP_DIR = DATA_DIR / 'uploaded_rfps'
UPLOAD_DOCS_DIR = DATA_DIR / 'uploaded_docs'

# Create directories
for directory in [DATA_DIR, UPLOAD_RFP_DIR, UPLOAD_DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============   PDF Extraction Settings ============
PDF_TEXT_THRESHOLD = 50
OCR_CONFIDENCE_THRESHOLD = 0.6

# ============ RAG SETTINGS  ============
USE_RAG_MATCHING = os.getenv('USE_RAG_MATCHING', 'true').lower() == 'true'

# Chunking Configuration
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# Database Performance
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))

# RAG Thresholds
RAG_CONFIDENCE_HIGH = 0.60  # Present
RAG_CONFIDENCE_MEDIUM = 0.45  # Review
RAG_CONFIDENCE_LOW = 0.30  # Missing

# Content Extraction
MAX_PAGES_TO_EXTRACT = int(os.getenv('MAX_PAGES_TO_EXTRACT', '0'))  # 0 = all pages

# Redis Cache (optional)
ENABLE_REDIS_CACHE = os.getenv('ENABLE_REDIS_CACHE', 'false').lower() == 'true'
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# ============ HYBRID RAG + LLM SETTINGS ============
USE_RAG_MATCHING = os.getenv('USE_RAG_MATCHING', 'true').lower() == 'true'
RAG_USE_LLM_VERIFICATION = os.getenv('RAG_USE_LLM_VERIFICATION', 'true').lower() == 'true'
RAG_TOP_K_CHUNKS = int(os.getenv('RAG_TOP_K_CHUNKS', '5'))  # Retrieve top 5 chunks

# LLM Verification Model (use GPT-4o-mini for cost savings)
RAG_VERIFICATION_MODEL = os.getenv('RAG_VERIFICATION_MODEL', 'gpt-4o-mini')
RAG_VERIFICATION_MAX_TOKENS = 500

# ============   Document Matching Settings ============
SENTENCE_TRANSFORMER_MODEL = 'all-MiniLM-L6-v2'
SIMILARITY_THRESHOLD_HIGH = 0.85
SIMILARITY_THRESHOLD_MEDIUM = 0.75
SIMILARITY_THRESHOLD_LOW = 0.70

# ============   API LLM SETTINGS ============
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
LLM_PROVIDER = 'auto'

# OpenAI Settings
OPENAI_MODEL = 'gpt-4o'
OPENAI_TEMPERATURE = 0.0
OPENAI_MAX_TOKENS = 6000
OPENAI_TIMEOUT = 60

# Anthropic Settings
ANTHROPIC_MODEL = 'claude-3-5-sonnet-20241022'
ANTHROPIC_TEMPERATURE = 0.1
ANTHROPIC_MAX_TOKENS = 4000
ANTHROPIC_TIMEOUT = 60

# ============   Extraction Mode ============
USE_HYBRID_EXTRACTION = False
USE_LLM_MATCHING = True
LLM_MATCHING_MODEL = OPENAI_MODEL
LLM_MATCHING_TEMPERATURE = 0.0
LLM_MATCHING_MAX_TOKENS = 3000
LLM_MATCHING_TIMEOUT = 90
LLM_MATCHING_BATCH_SIZE = 10

# Confidence calibration
LLM_CONFIDENCE_HIGH = 0.85
LLM_CONFIDENCE_MEDIUM = 0.70
LLM_CONFIDENCE_LOW = 0.55
LLM_CONFIDENCE_NONE = 0.0
ENABLE_TRADITIONAL_FALLBACK = True

# ============   Content Matching Settings ============
USE_CONTENT_MATCHING = True
MAX_CONTENT_LENGTH = 8000
CONTENT_WEIGHT = 0.40
FILENAME_WEIGHT = 0.60

ENABLE_SMART_VALIDATION = True
MIN_DOCUMENT_WORDS = 2
MAX_DOCUMENT_WORDS = 25
MIN_DOCUMENT_CHARS = 5

# ============   spaCy Settings ============
SPACY_MODEL = 'en_core_web_md'
SPACY_CONFIDENCE_THRESHOLD = 5
SPACY_KEYWORD_COVERAGE = 0.6

# Cost Control
MAX_INPUT_TOKENS = 30000
ENABLE_COST_TRACKING = True

# ============   Document Keywords ============
DOCUMENT_KEYWORDS = [
    'certificate', 'license', 'permit', 'insurance', 'registration',
    'declaration', 'statement', 'proof', 'evidence', 'document',
    'form', 'affidavit', 'agreement', 'contract', 'letter',
    'authorization', 'approval', 'clearance', 'compliance',
    'resume', 'cv', 'reference', 'financial', 'audit', 'report'
]

# ============   List Patterns ============
LIST_PATTERNS = [
    r'\d+\.\s+', r'[a-z]\)\s+', r'[A-Z]\)\s+',
    r'•\s+', r'-\s+', r'\*\s+',
    r'[ivxIVX]+\.\s+', r'\(\d+\)\s+', r'\([a-z]\)\s+'
]

# ============   File Upload Settings ============
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = ['pdf', 'docx', 'doc', 'txt', 'md', 'markdown', 'rtf', 'odt']

SUPPORTED_FORMATS = {
    'pdf': 'PDF Document',
    'docx': 'Word Document (DOCX)',
    'doc': 'Word Document (DOC)',
    'txt': 'Text File',
    'md': 'Markdown File',
    'markdown': 'Markdown File',
    'rtf': 'Rich Text Format',
    'odt': 'OpenDocument Text'
}

# ============   Output Settings ============
RESULT_COLUMNS = ['Required Document', 'Status', 'Matched File', 'Confidence Score']
STATUS_PRESENT = '✅ Present'
STATUS_MISSING = '❌ Missing'
STATUS_REVIEW = '⚠️ Review Needed'

# ============ ENHANCED DOCUMENT EXTRACTION SETTINGS ============
# Extraction Strategy
USE_ENHANCED_EXTRACTION = os.getenv('USE_ENHANCED_EXTRACTION', 'true').lower() == 'true'

# PyMuPDF4LLM Configuration
PYMUPDF4LLM_PAGE_CHUNKS = os.getenv('PYMUPDF4LLM_PAGE_CHUNKS', 'true').lower() == 'true'
PYMUPDF4LLM_WRITE_IMAGES = os.getenv('PYMUPDF4LLM_WRITE_IMAGES', 'false').lower() == 'true'
PYMUPDF4LLM_TABLE_STRATEGY = os.getenv('PYMUPDF4LLM_TABLE_STRATEGY', 'lines_strict')  # 'lines', 'lines_strict', 'explicit'
PYMUPDF4LLM_EXTRACT_WORDS = os.getenv('PYMUPDF4LLM_EXTRACT_WORDS', 'false').lower() == 'true'

# Table Handling
TABLE_AS_SINGLE_CHUNK = os.getenv('TABLE_AS_SINGLE_CHUNK', 'true').lower() == 'true'
TABLE_MAX_CHARS = int(os.getenv('TABLE_MAX_CHARS', '4000'))
MARKDOWN_TABLE_DETECTION = os.getenv('MARKDOWN_TABLE_DETECTION', 'true').lower() == 'true'

# Fallback Configuration
EXTRACTION_FALLBACK_ENABLED = os.getenv('EXTRACTION_FALLBACK_ENABLED', 'true').lower() == 'true'

# PaddleOCR Configuration
PADDLEOCR_USE_GPU = os.getenv('PADDLEOCR_USE_GPU', 'false').lower() == 'true'
PADDLEOCR_LANG = os.getenv('PADDLEOCR_LANG', 'en')
PADDLEOCR_SHOW_LOG = os.getenv('PADDLEOCR_SHOW_LOG', 'false').lower() == 'true'

POPPLER_PATH = os.getenv('POPPLER_PATH', None)


# ============ COMPLIANCE VALIDATION SETTINGS ============

# Enable enhanced validation with structured data extraction
ENABLE_STRUCTURED_VALIDATION = os.getenv('ENABLE_STRUCTURED_VALIDATION', 'true').lower() == 'true'

# Validation confidence thresholds
VALIDATION_CONFIDENCE_HIGH = float(os.getenv('VALIDATION_CONFIDENCE_HIGH', '0.85'))
VALIDATION_CONFIDENCE_MEDIUM = float(os.getenv('VALIDATION_CONFIDENCE_MEDIUM', '0.65'))

# Numeric validation settings
NUMERIC_EXTRACTION_PRECISION = int(os.getenv('NUMERIC_EXTRACTION_PRECISION', '2'))  # Decimal places

# Date validation settings
DATE_VALIDATION_BUFFER_DAYS = int(os.getenv('DATE_VALIDATION_BUFFER_DAYS', '0'))  # Grace period for expiry

# Count validation settings
COUNT_VALIDATION_STRICT = os.getenv('COUNT_VALIDATION_STRICT', 'true').lower() == 'true'

print(f"✓ Structured Validation: {'ENABLED' if ENABLE_STRUCTURED_VALIDATION else 'DISABLED'}")