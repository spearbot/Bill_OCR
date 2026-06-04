import os
import secrets
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Medical Bill OCR Platform"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    PADDLEOCR_USE_GPU: bool = False
    PADDLEOCR_LANG: str = "en"

    UPLOAD_DIR: str = "uploads"
    DATA_DIR: str = "data"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list = ["jpg", "jpeg", "png", "pdf"]

    # Google Sheets (optional)
    GOOGLE_SHEETS_ENABLED: bool = False
    GOOGLE_SHEET_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""

    # Storage mode: "excel", "google_sheets", "both"
    STORAGE_MODE: str = "excel"

    CORS_ORIGINS: list = ["http://localhost:3000"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_urlsafe(32)

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
