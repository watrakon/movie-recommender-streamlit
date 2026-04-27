from pathlib import Path
import os
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# ตั้งค่า TMDB API key จาก environment variable (ถ้าไม่ตั้งจะใช้ฟีเจอร์ปก TMDB ไม่ได้)
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///movies.db")
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
PORT: int = int(os.getenv("PORT", "8501"))
ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
