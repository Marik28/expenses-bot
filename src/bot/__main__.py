import logging

import dotenv
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

dotenv.load_dotenv()
from .bot import dp
from .middlewares.auth import AuthMiddleware

log = logging.getLogger()
logging.basicConfig(level="INFO")

dp.setup_middleware(LoggingMiddleware(log))
dp.middleware.setup(AuthMiddleware())
executor.start_polling(dp, skip_updates=True)
