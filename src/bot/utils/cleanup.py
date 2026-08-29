"""Отложенное удаление сообщений.

Используется командами статистики (`/period`, `/trend`), чтобы через час убрать
из чата и команду пользователя, и ответ бота с графиками. Задачи живут в текущем
event loop; при рестарте бота незапланированные удаления теряются — как и
in-memory FSM.
"""
import asyncio
import logging
from collections.abc import Iterable

from aiogram import Bot
from aiogram.utils import exceptions

logger = logging.getLogger(__name__)

DELETE_AFTER = 60 * 60  # секунд — сообщения команд статистики живут час

_pending: set[asyncio.Task] = set()


async def _delete_later(bot: Bot, chat_id: int, message_ids: Iterable[int], delay: int) -> None:
    await asyncio.sleep(delay)
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except (exceptions.MessageToDeleteNotFound, exceptions.MessageCantBeDeleted):
            pass
        except exceptions.TelegramAPIError as error:
            logger.warning("Не удалось удалить сообщение %s в чате %s: %s", message_id, chat_id, error)


def schedule_deletion(bot: Bot, chat_id: int, *message_ids: int | None, delay: int = DELETE_AFTER) -> None:
    """Запланировать удаление сообщений ``message_ids`` в чате ``chat_id`` через ``delay`` секунд."""
    ids = [message_id for message_id in message_ids if message_id is not None]
    if not ids:
        return

    task = asyncio.create_task(_delete_later(bot, chat_id, ids, delay))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
