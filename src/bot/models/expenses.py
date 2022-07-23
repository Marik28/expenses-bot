from dataclasses import dataclass

from aiogram.types import MediaGroup


@dataclass
class DailyStatistics:
    details: str
    aggregated: str
    charts: MediaGroup
