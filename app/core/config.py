import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "NutriAI API")
    API_TOKEN: str = os.getenv("API_TOKEN", "nutri_dev_secret_token_123")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()