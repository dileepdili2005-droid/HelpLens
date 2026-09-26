import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if it exists
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    """Application configuration settings."""
    SECRET_KEY = os.getenv("SECRET_KEY", "helplens-hackathon-secure-key-2026")
    
    # Gemini API configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    
    # File upload settings
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
    
    # Database configuration (SQLite by default, zero external setup)
    DATABASE_PATH = BASE_DIR / "helplens.db"
    USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() in ("true", "1", "yes")
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Ensure upload directory exists
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
