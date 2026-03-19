"""
Application settings — reads from .env file or environment variables.

Think of this as the app's "control panel" where all configuration lives.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    DATABASE_URL: The connection string for PostgreSQL.
    It tells the app where the database lives and how to log in.
    Format: postgresql+asyncpg://username:password@host:port/database_name
    """

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/freight_agent"

    class Config:
        env_file = ".env"


# Create one instance the whole app shares
settings = Settings()
