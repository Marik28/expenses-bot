import datetime as dt
from zoneinfo import ZoneInfo

RU_MONTHS = (
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
)
RU_MONTHS_SHORT = (
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
)


def localnow() -> dt.datetime:
    return dt.datetime.now(ZoneInfo("Asia/Almaty"))


def month_label(day: dt.date) -> str:
    """``date(2026, 8, ...)`` -> ``'Август 2026'``."""
    return f"{RU_MONTHS[day.month - 1]} {day.year}"


def month_label_short(day: dt.date) -> str:
    """``date(2026, 8, ...)`` -> ``'Авг 2026'`` (для тесных мест, например кнопок)."""
    return f"{RU_MONTHS_SHORT[day.month - 1]} {day.year}"


def month_bounds(day: dt.date) -> tuple[dt.date, dt.date]:
    """Границы месяца, которому принадлежит ``day``, но не позже сегодняшнего
    дня (для текущего месяца)."""
    start = day.replace(day=1)
    next_month = (start.replace(year=start.year + 1, month=1) if start.month == 12
                  else start.replace(month=start.month + 1))
    end = min(next_month - dt.timedelta(days=1), localnow().date())
    return start, end
