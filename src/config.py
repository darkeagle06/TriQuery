"""
Configuration module for TriQuery.
Loads environment variables from .env file with safe fallbacks and validation.
Never hardcodes passwords or sensitive credentials.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the TriQuery project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()  # Fallback to current working directory or process environment


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "127.0.0.1")
    port: int = int(os.getenv("DB_PORT", "3306"))
    name: str = os.getenv("DB_NAME", "triquery_db")
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "")
    charset: str = os.getenv("DB_CHARSET", "utf8mb4")
    driver: str = os.getenv("DB_DRIVER", "mysql").lower()
    sqlite_fallback: bool = os.getenv("DB_TEST_SQLITE_FALLBACK", "false").lower() in ("true", "1", "yes")
    sqlite_path: str = os.getenv("DB_SQLITE_PATH", "")


@dataclass(frozen=True)
class VectorConfig:
    backend: str = os.getenv("VECTOR_BACKEND", "tfidf")
    top_k: int = int(os.getenv("VECTOR_TOP_K", "5"))
    similarity_threshold: float = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.15"))


@dataclass(frozen=True)
class AppConfig:
    env: str = os.getenv("TRIQUERY_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    db: DatabaseConfig = DatabaseConfig()
    vector: VectorConfig = VectorConfig()
    base_dir: Path = BASE_DIR
    database_dir: Path = BASE_DIR / "database"


# Singleton instance
config = AppConfig()
