import datetime as dt
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str
    telegram_token: str
    allowed_users: list[int]
    exclude_categories: list[int]
    daily_stats_hour: int = 9
    daily_stats_minute: int = 0
    scheduler_timezone: str = "Asia/Almaty"

    # Конвертация валют (курсы Нацбанка РК)
    currency_api_url: str = "https://nationalbank.kz/rss/get_rates.cfm"
    redis_url: str = "redis://localhost:6379/0"
    # В конфиге указывается числом дней, хранится как timedelta.
    currency_cache_ttl_days: dt.timedelta = dt.timedelta(days=30)

    @field_validator("currency_cache_ttl_days", mode="before")
    @classmethod
    def _ttl_days_to_timedelta(cls, value: object) -> dt.timedelta:
        if isinstance(value, dt.timedelta):
            return value

        return dt.timedelta(days=int(value))


settings = Settings()
