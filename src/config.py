from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    serper_api_key: str
    openai_model: str = "gpt-4o-mini"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "company_scraper"

    model_config = SettingsConfigDict(env_file=(".env", "src/.env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
