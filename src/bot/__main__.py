from aiogram.utils import executor

from .bot import dp
from .middlewares.auth import AuthMiddleware

dp.middleware.setup(AuthMiddleware())
executor.start_polling(dp, skip_updates=True)
