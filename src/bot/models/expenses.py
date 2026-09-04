from dataclasses import dataclass

from aiogram.types import MediaGroup


@dataclass
class DailyStatistics:
    details: str
    aggregated: str
    charts: MediaGroup


@dataclass
class PeriodStatistics:
    top_ten: str
    daily: str
    charts: MediaGroup


@dataclass
class CategoryTrendStatistics:
    charts: MediaGroup


@dataclass
class CategoryMonthStatistics:
    details: str
    charts: MediaGroup
