from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / '.env', extra='ignore', hide_input_in_errors=True)
    database_url: str
    cors_origins: list[str] = ['http://localhost:5173']
    environment: str = 'development'
    admin_emails: list[str] = []
    portone_api_secret: str = ''
    portone_webhook_secret: str = ''
    portone_store_id: str = ''
    portone_channel_key: str = ''
    portone_api_base_url: str = 'https://api.portone.io'
    payments_enabled: bool = False
    refunds_enabled: bool = False
    culture_api_key: str = ''
    culture_api_base_url: str = 'https://apis.data.go.kr/B553457/nopenapi/rest/publicperformancedisplays'

    @field_validator('database_url')
    @classmethod
    def maria_only(cls, value: str) -> str:
        if not value.startswith(('mysql+pymysql://', 'mariadb+pymysql://')):
            raise ValueError('MariaDB / PyMySQL DATABASE_URL is required; SQLite is not supported.')
        return value

    @property
    def payment_ready(self) -> bool:
        return self.payments_enabled and all((self.portone_api_secret, self.portone_store_id, self.portone_channel_key, self.portone_webhook_secret))


@lru_cache
def get_settings() -> Settings:
    return Settings()
