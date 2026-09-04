from aiogram import Bot, types

BOT_COMMANDS = [
    types.BotCommand("start", "Зарегистрироваться в боте"),
    types.BotCommand("help", "Помощь"),
    types.BotCommand("balance", "Текущий баланс"),
    types.BotCommand("today", "Сумма трат за сегодня"),
    types.BotCommand("day", "Статистика за выбранный день"),
    types.BotCommand("period", "Статистика за период"),
    types.BotCommand("trend", "Тренд трат по категории за год"),
    types.BotCommand("category", "Траты по категории за месяц"),
    types.BotCommand("add_category", "Добавить категорию"),
    types.BotCommand("cancel", "Отменить текущее действие"),
]


async def set_bot_commands(bot: Bot):
    """Регистрирует команды бота, чтобы они отображались в меню Telegram."""
    await bot.set_my_commands(BOT_COMMANDS)
