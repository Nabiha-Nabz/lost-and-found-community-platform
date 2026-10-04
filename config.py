import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-this-secret-before-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'lostfound.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    ADMIN_REGISTRATION_CODE = os.getenv("ADMIN_REGISTRATION_CODE", "LostFoundAdmin2026")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost"
