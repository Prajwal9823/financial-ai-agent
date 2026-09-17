"""
Central configuration.
Everything here is read from environment variables (.env) so that no
secret ever lives in source code. See .env.example for the full list.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- LLM ---
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.6-flash"
    llm_fallback_model: str = ""

    # --- Optional external data keys (app works without these via yfinance/SEC) ---
    alpha_vantage_api_key: str = ""

    # --- App behaviour ---
    cache_ttl_seconds: int = 900          # 15 min default cache lifetime
    max_news_articles: int = 10
    sec_user_agent: str = "FinancialAIAgent research-project contact@example.com"

    # --- CORS ---
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so we parse the .env file only once."""
    return Settings()
