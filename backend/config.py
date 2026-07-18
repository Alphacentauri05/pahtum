import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # JWT Auth Settings
    JWT_SECRET: str = "super-secret-key-please-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours

    # CouchDB Settings
    COUCHDB_URL: str = "http://127.0.0.1:5984"
    COUCHDB_USERNAME: str = "admin"
    COUCHDB_PASSWORD: str = "admin"
    COUCHDB_DATABASE: str = "pahtum"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
