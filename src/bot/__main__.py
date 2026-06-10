import logging

import dotenv
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

dotenv.load_dotenv()
from .bot import bot, dp
from .middlewares.auth import AuthMiddleware
from .scheduler import build_scheduler

logger = logging.getLogger()
logging.basicConfig(level="INFO")

dp.setup_middleware(LoggingMiddleware(logger))
dp.middleware.setup(AuthMiddleware())

scheduler = build_scheduler(bot)


async def on_startup(dp):
    scheduler.start()
    logger.info("Scheduler started")


async def on_shutdown(dp):
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )
