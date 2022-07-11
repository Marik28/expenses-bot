from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

from ..settings import settings


class AuthMiddleware(BaseMiddleware):
    async def on_pre_process_update(self, update: types.Update, data: dict):
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user
        else:
            raise CancelHandler()

        if user.id not in settings.allowed_users:
            raise CancelHandler()
