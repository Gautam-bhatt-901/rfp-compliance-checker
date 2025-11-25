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

# ============ NEW: API SETTINGS ============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# CORS settings
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rfp_app.db")
# For PostgreSQL: DATABASE_URL = "postgresql://user:password@localhost/rfp_db"

# ============   Directory Configuration ============
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / 'data'
UPLOAD_RFP_DIR = DATA_DIR / 'uploaded_rfps'
UPLOAD_DOCS_DIR = DATA_DIR / 'uploaded_docs'

# Create directories
for directory in [DATA_DIR, UPLOAD_RFP_DIR, UPLOAD_DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============   PDF Extraction Settings ============
PDF_TEXT_THRESHOLD = 100
OCR_CONFIDENCE_THRESHOLD = 0.5

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
MAX_INPUT_TOKENS = 8000
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
