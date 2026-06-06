from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./aiplatforma.db"
    SECRET_KEY: str = "aiplatforma-dev-secret-key-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None

    GOOGLE_DRIVE_CREDENTIALS_FILE: Optional[str] = "credentials.json"
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = None

    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 52428800  # 50MB

    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
