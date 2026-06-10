import datetime as dt
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import ParseMode
from aiogram.utils.markdown import code
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .db.database import Session
from .services.expenses import ExpensesService
from .services.users import UsersService
from .settings import settings

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo(settings.scheduler_timezone)


async def _send_to_user(bot: Bot, user_id: int, day: dt.date) -> None:
    expense_service = ExpensesService(Session())

    try:
        stats = expense_service.get_daily_statistics(user_id, day)
    except Exception as exc:
        logger.exception("Failed to collect stats for %s on %s: %s", user_id, day, exc)
        await bot.send_message(
            user_id,
            f"⚠️ Не удалось получить статистику за {day.strftime('%d.%m.%Y')}.",
            parse_mode=ParseMode.HTML,
        )
        return

    if stats is None:
        await bot.send_message(
            user_id,
            f"За вчера ({day.strftime('%d.%m.%Y')}) трат не обнаружено.",
            parse_mode=ParseMode.HTML,
        )
        return

    await bot.send_message(
        user_id,
        code(stats.details),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    if stats.charts:
        await bot.send_media_group(user_id, stats.charts)


async def send_daily_stats(bot: Bot) -> None:
    yesterday = (dt.datetime.now(LOCAL_TZ) - dt.timedelta(days=1)).date()

    user_service = UsersService(Session())
    try:
        user_ids = user_service.get_all_users()
    except Exception as exc:
        logger.exception("Failed to fetch user list: %s", exc)
        return

    logger.info("Sending daily stats for %s to %d users", yesterday, len(user_ids))

    for user_id in user_ids:
        try:
            await _send_to_user(bot, user_id, yesterday)
        except Exception as exc:
            logger.exception("Failed to send stats to user %s: %s", user_id, exc)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=LOCAL_TZ)
    scheduler.add_job(
        send_daily_stats,
        CronTrigger(hour=settings.daily_stats_hour, minute=settings.daily_stats_minute),
        args=[bot],
        id="daily_stats",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler
