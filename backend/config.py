from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    CONNECTION_URI: str

    FINNHUB_API_KEY: str
    NEWS_API_KEY: str
    OPENAI_API_KEY: str
    ALPHA_VANTAGE_API_KEY: str

    BSKY_IDENTIFIER: str
    BSKY_PASSWORD: str

    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str
    
    PORT: int = 8000
    SENTIMENT_ANALYZER_URL: str = "http://localhost:8001"
    FRONTEND_URL: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        

settings = Settings()