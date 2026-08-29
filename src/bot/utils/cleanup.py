"""Отложенное удаление сообщений"""
import asyncio
import datetime as dt
import logging
from collections.abc import Iterable

from aiogram import Bot
from aiogram.utils import exceptions

logger = logging.getLogger(__name__)

DELETE_AFTER = dt.timedelta(hours=1)

_pending: set[asyncio.Task] = set()


async def _delete_later(bot: Bot, chat_id: int, message_ids: Iterable[int], after: dt.timedelta) -> None:
    delay = after.total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except (exceptions.MessageToDeleteNotFound, exceptions.MessageCantBeDeleted) as e:
            logger.info("Failed to delete message %s: %r", message_id, e)
        except exceptions.TelegramAPIError as error:
            logger.warning("Не удалось удалить сообщение %s в чате %s: %s", message_id, chat_id, error)


def schedule_deletion(
        bot: Bot,
        chat_id: int,
        *message_ids: int,
        after: dt.timedelta = DELETE_AFTER,
) -> None:
    """Запланировать удаление сообщений ``message_ids`` в чате ``chat_id`` через ``after``."""
    if not message_ids:
        return

    task = asyncio.create_task(_delete_later(bot, chat_id=chat_id, message_ids=message_ids, after=after))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
