import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "NutriAI API")
    API_TOKEN: str = os.getenv("API_TOKEN", "nutri_dev_secret_token_123")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID") or None


settings = Settings()