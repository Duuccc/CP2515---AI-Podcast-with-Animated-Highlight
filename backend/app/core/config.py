from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "AI Podcast Highlight Generator"
    DEBUG: bool = True
    
    # Database (optional for now)
    DATABASE_URL: Optional[str] = None
    
    # File storage
    UPLOAD_DIR: str = "./uploads"
    OUTPUT_DIR: str = "./outputs"
    MAX_FILE_SIZE: int = 104857600  # 100MB
    
    # Allowed audio formats
    ALLOWED_EXTENSIONS: set = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    
    # API Keys (optional for now)
    OPENAI_API_KEY: Optional[str] = None
    
    # AI Enhancement Features
    USE_AI_HOOK: bool = True  # Enable GPT-4 hook generation (fast, cheap)
    USE_AI_BACKGROUND: bool = False  # Enable DALL-E background generation (slower, costs ~$0.04 per video)
    
    # Redis for task queue (optional for now)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Processing settings
    HIGHLIGHT_DURATION: int = 60  # seconds
    MIN_HIGHLIGHT_DURATION: int = 15
    MAX_HIGHLIGHT_DURATION: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields in .env without errors

settings = Settings()