from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from decimal import Decimal
import typing as t
import hishel
import xmltodict
from hishel.httpx import AsyncCacheClient
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis

from ..settings import settings
from ..utils.datetime import localnow
from ..utils.parsing import BASE_CURRENCY

logger = logging.getLogger(__name__)

_MAX_LOOKBACK_DAYS = 7
"""На сколько дней назад отступать в поисках рабочего дня (выходные/праздники), если на запрошенную дату курс ещё не опубликован."""


class CurrencyError(Exception):
    """Не удалось получить курс валюты (неизвестный код или нет данных)."""


@dataclass(frozen=True)
class Conversion:
    """Результат конвертации: сумма в базовой валюте и применённый курс."""

    amount: Decimal
    rate: Decimal


class RateItem(BaseModel):
    """Курс одной валюты из ответа Нацбанка (`<item>`)."""

    code: str = Field(alias="title")
    rate: Decimal = Field(alias="description")
    quant: int = 1  # за сколько единиц указан курс (напр. 10 RUB, 100 IRR)

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: t.Any) -> str:
        return str(value or "").strip().upper()

    @property
    def per_unit(self) -> Decimal:
        """Курс за одну единицу валюты."""
        return self.rate / self.quant


class NationalBankRates(BaseModel):
    """Ответ Нацбанка (`<rates>`) со списком курсов валют."""

    items: list[RateItem] = Field(default_factory=list, alias="item")

    @field_validator("items", mode="before")
    @classmethod
    def _ensure_list(cls, value: t.Any) -> list:
        if value is None:
            return []
        # xmltodict отдаёт единственный <item> словарём, а не списком.
        if isinstance(value, dict):
            return [value]
        return value


class CurrencyConverter:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url)
        self._client = AsyncCacheClient(
            storage=hishel.AsyncRedisStorage(
                client=self._redis,
                ttl=settings.currency_cache_ttl_days.total_seconds(),
            ),
            policy=hishel.FilterPolicy(),
            timeout=30,
        )

    async def aclose(self) -> None:
        """Закрывает httpx-клиент и соединение с Redis (вызывать на остановке бота)."""
        await self._client.aclose()
        await self._redis.aclose()

    async def convert(self, amount: Decimal, currency: str, on_date: dt.date | None = None) -> Conversion:
        """Переводит `amount` из `currency` в базовую валюту на дату `on_date`.

        Возвращает :class:`Conversion` — сконвертированную сумму и применённый курс.
        """
        currency = currency.upper()
        if currency == BASE_CURRENCY:
            return Conversion(amount=Decimal(amount).quantize(Decimal("0.01")), rate=Decimal(1))

        rate = await self.get_rate(currency, on_date or localnow().date())
        converted = (Decimal(amount) * rate).quantize(Decimal("0.01"))
        return Conversion(amount=converted, rate=rate)

    async def get_rate(self, currency: str, on_date: dt.date) -> Decimal:
        """Курс одной единицы `currency` в базовой валюте на дату `on_date`."""
        currency = currency.upper()
        if currency == BASE_CURRENCY:
            return Decimal(1)

        rates = await self._rates_for_nearest_working_day(on_date)
        entry = rates.get(currency)
        if entry is None:
            raise CurrencyError(f"Нет курса для валюты {currency} на {on_date.isoformat()}")

        return entry.per_unit

    async def _rates_for_nearest_working_day(self, on_date: dt.date) -> dict[str, RateItem]:
        """Курсы на дату; если их нет — отступаем к последнему рабочему дню."""
        day = on_date
        for _ in range(_MAX_LOOKBACK_DAYS + 1):
            rates = await self._fetch(day)
            if rates:
                return rates
            day -= dt.timedelta(days=1)

        raise CurrencyError(f"Нет курсов Нацбанка около {on_date.isoformat()}")

    async def _fetch(self, day: dt.date) -> dict[str, RateItem]:
        params = {"fdate": day.strftime("%d.%m.%Y")}
        response = await self._client.get(settings.currency_api_url, params=params)
        response.raise_for_status()

        parsed = xmltodict.parse(response.text)
        rates = NationalBankRates.model_validate(parsed.get("rates") or {})
        return {item.code: item for item in rates.items if item.code}
