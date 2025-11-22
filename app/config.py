import os
from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"  # development or production
    MODEL_PROVIDER: str = "mock"
    GEMINI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    KB_PATH: str = "data/kb.json"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"  # default, overridden in get_settings()

@lru_cache()
def get_settings() -> Settings:
    """
    Load settings based on APP_ENV. Look for .env.{env} first,
    then fall back to .env.
    """
    # If APP_ENV already present in process env, use it, else default
    env = os.environ.get("APP_ENV", None)
    # prefer explicit .env.<env> if exists
    env_file = None
    if env:
        candidate = f".env.{env}"
        if os.path.exists(candidate):
            env_file = candidate
    # fallback to .env
    if env_file is None and os.path.exists(".env"):
        env_file = ".env"

    if env_file:
        return Settings(_env_file=env_file)
    # else load defaults / environment
    return Settings()
