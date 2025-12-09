from pydantic_settings import BaseSettings
from typing import Optional
import urllib.parse

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Red Inteligente API de Autenticación"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Code verification settings
    CODE_EXPIRATION_MINUTES: int = 30
    CODE_RESEND_DELAY_MINUTES: int = 2
    CODE_MAX_RESEND_PER_HOUR: int = 5
    
    # Cleanup settings
    CLEANUP_INTERVAL_MINUTES: int = 60
    ENABLE_AUTOMATIC_CLEANUP: bool = True
    
    # Database settings - PostgreSQL
    DB_SERVER: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_TIMEOUT: int = 30
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True

    # Email settings SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    FROM_EMAIL: str = "noreply@redinteligente.com"
    FROM_NAME: str = "Red Inteligente"
    
    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:8009"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    
    # CORS settings
    CORS_ORIGINS: str = "*"

    @property
    def database_url(self) -> str:
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        encoded_user = urllib.parse.quote_plus(self.DB_USER)
        return f"postgresql+psycopg2://{encoded_user}:{encoded_password}@{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def cors_origins_list(self) -> list:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()