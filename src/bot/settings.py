from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str
    telegram_token: str
    allowed_users: list[int]
    exclude_categories: list[int]
    daily_stats_hour: int = 9
    daily_stats_minute: int = 0
    scheduler_timezone: str = "Asia/Almaty"


settings = Settings()
