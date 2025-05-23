from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, field_validator, Field

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    All sensitive/configurable values should be set via environment variables.
    """
    PROJECT_NAME: str = Field("Neo Events", env="PROJECT_NAME")
    VERSION: str = Field("1.0.0", env="VERSION")
    API_V1_STR: str = Field("/api", env="API_V1_STR")

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Must be set in env
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Database
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    SQLALCHEMY_DATABASE_URI: Optional[str] = Field(None, env="DATABASE_URL")

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str) and v:
            return v
        
        # Build from components
        user = info.data.get("POSTGRES_USER")
        password = info.data.get("POSTGRES_PASSWORD")
        server = info.data.get("POSTGRES_SERVER")
        db = info.data.get("POSTGRES_DB")
        
        if not all([user, password, server, db]):
            raise ValueError("Database credentials are not fully set in environment variables.")
        
        return f"postgresql://{user}:{password}@{server}/{db}"

    # Redis
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 