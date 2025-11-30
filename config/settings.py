import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
CACHE_DIR = DATA_DIR / "cache"
EXPORTS_DIR = DATA_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"
DATABASE_PATH = BASE_DIR / "database" / "applications.db"

# Create directories if they don't exist
for dir_path in [UPLOADS_DIR, CACHE_DIR, EXPORTS_DIR, LOGS_DIR, DATABASE_PATH.parent]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
COMET_API_KEY = os.getenv("COMET_API_KEY")
COMET_PROJECT_NAME = os.getenv("COMET_PROJECT_NAME", "pfe-matcher")
COMET_WORKSPACE = os.getenv("COMET_WORKSPACE")

# Gmail Configuration
GMAIL_SCOPES = [os.getenv("GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.send")]
GMAIL_CREDENTIALS_PATH = BASE_DIR / "config" / "credentials.json"
GMAIL_TOKEN_PATH = BASE_DIR / "config" / "token.json"

# Application Settings
MAX_EMAILS_PER_DAY = int(os.getenv("MAX_EMAILS_PER_DAY", 90))
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", 60))

# Model Settings
GEMINI_MODEL_NAME = "gemini-flash-latest"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Cache Settings
CACHE_TTL_HOURS = 24
