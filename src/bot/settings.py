from pydantic import BaseSettings


class Settings(BaseSettings):
    db_url: str
    telegram_token: str
    allowed_users: list[int]
    exclude_categories: list[int]


settings = Settings()
