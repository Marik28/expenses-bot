# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Обзор

Telegram-бот для учёта личных расходов и доходов (aiogram 2.x, long polling) с хранением в PostgreSQL и генерацией статистики в виде текстовых таблиц и графиков (pandas + matplotlib). Интерфейс бота — на русском языке; сообщения и кнопки пишутся по-русски.

## Команды

Зависимости управляются через **uv**. Python строго `>=3.10,<3.11`.

```bash
uv sync # установка зависимостей (включая dev-группу)

# Тесты — обязательно PYTHONPATH=src, иначе `import bot` не резолвится
PYTHONPATH=src uv run pytest tests/ -q

# Локальный запуск бота (нужны переменные окружения, см. .env-example)
PYTHONPATH=src uv run python -m bot

# Миграции — запускаются из каталога src/ (alembic.ini лежит там)
cd src && uv run alembic upgrade head
cd src && uv run alembic revision --autogenerate -m "описание"

# Docker
docker compose up --build        # поднимает postgres:12 + redis:7 + бота
```

Линтера/форматтера в проекте нет.

## Конфигурация

`src/bot/settings.py` — единственный источник настроек (`pydantic-settings`, инстанс `settings` создаётся на импорте). `.env` **не** подхватывается автоматически самим `Settings`: `dotenv.load_dotenv()` вызывается в `src/bot/__main__.py` **до** импорта `bot.bot`. Поэтому любой скрипт/точка входа мимо `__main__.py` (в т.ч. alembic) требует, чтобы переменные уже были в окружении.

Ключевые переменные (`.env-example`): `DB_URL`, `TELEGRAM_TOKEN`, `ALLOWED_USERS` (белый список telegram id), `EXCLUDE_CATEGORIES` (id категорий, исключаемых из статистики — например, долги), `DAILY_STATS_HOUR/MINUTE`, `SCHEDULER_TIMEZONE` (по умолчанию `Asia/Almaty`, тот же TZ прописан в docker-compose). Для конвертации валют: `REDIS_URL`, `CURRENCY_CACHE_TTL_DAYS`, опционально `CURRENCY_API_URL`.

Время всегда берётся через `utils/datetime.localnow()` (aware `datetime` в `Asia/Almaty`), а не `datetime.now()` — важно для «сегодня» в статистике и для даты курса.

## Архитектура

Слои (`src/bot/`):

- **`bot.py`** — все хендлеры aiogram в одном модуле; здесь же создаются `bot`, `dp`, `MemoryStorage`. Глобальный `@dp.errors_handler` ловит любое исключение, шлёт пользователю имя класса ошибки и сбрасывает FSM-состояние.
- **`middlewares/auth.py`** — `AuthMiddleware.on_pre_process_update` бросает `CancelHandler`, если `user.id` не в `settings.allowed_users`. Это единственная авторизация; апдейты без message/callback_query тоже отбрасываются.
- **`services/`** — вся работа с БД. Каждый сервис наследует `BaseService`, принимает `Session` в конструктор и закрывает её в `__del__`. Хендлеры создают сервис на запрос: `ExpensesService(Session())`. Сервисы синхронные и вызываются напрямую из async-хендлеров (блокирующие вызовы в event loop — так исторически сложилось).
- **`db/`** — `database.py` создаёт `engine`/`Session`/`Base` и в конце импортирует модели (важно для `Base.metadata` в alembic). SQLAlchemy 1.4 style (`session.query(...)`).
- **`models/expenses.py`** — dataclass'ы `DailyStatistics`/`PeriodStatistics` (DTO с текстом и `MediaGroup` графиков); не путать с `db/models/` (ORM-модели).
- **`helpers.py`** — фабрики inline-клавиатур и три `CallbackData`-префикса: `ctgr` (категория), `exp` (действие при добавлении), `op` (доход/расход).
- **`scheduler.py`** — `AsyncIOScheduler` с одним cron-джобом `daily_stats`: рассылает всем пользователям из БД статистику за вчера. Стартует/останавливается в `on_startup`/`on_shutdown` в `__main__.py`.
- **`services/currency.py`** — `CurrencyConverter` (см. раздел «Конвертация валют»). В отличие от остальных сервисов **не** наследует `BaseService` и не работает с БД; единый инстанс `converter` создаётся в `bot.py` и закрывается в `on_shutdown` (`converter.aclose()`).
- **`utils/parsing.py`** — `EXPENSE_REGEX` (скомпилированный) + `parse_expense`, возвращающий dataclass `ParsedExpense` (`amount`, `currency`, `comment`, свойство `is_kzt`); единственный покрытый тестами модуль.
- **`utils/datetime.py`** — `localnow()`, единый источник текущего времени (TZ `Asia/Almaty`).

### Как добавляется трата

Любое сообщение, подходящее под `EXPENSE_REGEX` (`сумма[КОД] [комментарий]`), запускает диалог: `parse_expense` возвращает `ParsedExpense`, сумма конвертируется в тенге, и в FSM кладутся `original_amount` (исходная сумма), `currency`, `amount` (в тенге), `rate` (курс) и `comment`. Дальше пользователь через inline-кнопки выбирает тип операции, категорию (обязательна — кнопка «Сохранить» появляется только после неё, флаг `can_save`), опционально дату и комментарий. Сохранение происходит в `save_expense`.

**Формат валюты**: 3-буквенный ISO-код пишется **слитно суффиксом** к сумме (`100usd`, `50EUR кофе`), регистр не важен. Код через пробел (`100 usd`) валютой не считается и уходит в комментарий — так его не спутать с текстом. Префикс (`USD100`) не поддерживается. Без кода валюта — `BASE_CURRENCY` (`KZT`), конвертация не выполняется. Валидность кода не проверяется при парсинге — неизвестный код упадёт `CurrencyError` при обращении к API.

Важные инварианты:
- **Дата курса**: `amount` (в тенге) хранится по курсу на дату расхода. При смене даты в календаре (`process_date_selection`) сумма пересчитывается из `original_amount` по курсу на выбранную дату; при не-тенговой валюте и в `process_add_expense`, и в `process_date_selection` ответ показывает строку конвертации (`💱 … ≈ … KZT (курс …)`).
- **Знак суммы**: расход пишется в БД с минусом, доход — с плюсом; флаг `is_expense` хранится отдельно. В статистике сумма снова инвертируется (`df["amount"] = -df["amount"]`), чтобы показывать положительные числа.
- **Баланс пользователя не считается в Python.** `users.balance` обновляется триггером PostgreSQL `add_balance` (создан в миграции `002_..._add_balance`), срабатывающим на insert в `expenses`. Изменения логики баланса — это новая миграция, а не код сервиса.
- **FSM в памяти** (`MemoryStorage`): при рестарте незавершённые диалоги теряются. Одновременно вести несколько добавлений нельзя (известное ограничение, см. TODO в `bot.py`).

### Статистика

`ExpensesService` строит запрос, читает его через `pd.read_sql(query.statement, ...)` в DataFrame, агрегирует по категориям и рендерит графики через `df.plot.<type>()` в `BytesIO` → `InputMediaPhoto`. Текстовые таблицы отправляются как `code(...)` с `ParseMode.MARKDOWN_V2`. Категории из `settings.exclude_categories` отфильтровываются на уровне SQL.

### Конвертация валют

`services/currency.py` — `CurrencyConverter`:
- **Источник курсов** — API Нацбанка РК: `GET {CURRENCY_API_URL}?fdate=DD.MM.YYYY` (XML на конкретную дату). Ответ парсится `xmltodict` → dict, затем валидируется pydantic-моделями `NationalBankRates` / `RateItem` (валидатор нормализует код, `_ensure_list` оборачивает единственный `<item>` в список; курс указан за `quant` единиц, `per_unit = rate / quant`).
- **`convert(amount, currency, on_date=None)`** возвращает dataclass `Conversion(amount, rate)` — сумму в тенге и применённый курс за единицу. Для `BASE_CURRENCY` возвращает сумму как есть с `rate=1`.
- **Выходные/праздники**: если на дату курса нет, отступает назад по дню до `_MAX_LOOKBACK_DAYS` (последний рабочий день).
- **Кэш** — `hishel` поверх httpx с Redis-хранилищем (`AsyncRedisStorage`, TTL из `CURRENCY_CACHE_TTL_DAYS`). Нацбанк не отдаёт cache-заголовки, поэтому используется `hishel.FilterPolicy` с `response_filters=[_SuccessfulRatesFilter()]`: кэшируется только успешный (2xx) ответ, где реально есть `<item>`. Ключ кэша — URL, т.е. каждая дата отдельно. Запросы асинхронные (`AsyncCacheClient`).
- Инстанс `converter` в `bot.py` держит httpx-клиент и соединение Redis на всё время работы; закрывается в `on_shutdown` через `converter.aclose()`.

docker-compose поднимает сервис `redis:7-alpine` (том `redis`, `depends_on` у бота).

### Миграции

`src/migrations/versions/` — файлы вручную префиксуются порядковым номером (`001_`, `002_`, `003_`), при этом revision id остаются сгенерированными хешами. `env.py` берёт URL из `settings.db_url` (offline) или `bot.db.database.engine` (online), поэтому alembic импортирует пакет `bot` и требует настроенного окружения. Автогенерация не увидит SQL-триггеры — их пишут руками через `op.execute`.

## Тесты

`tests/` содержит только юнит-тесты парсинга; конфигурации pytest в `pyproject.toml` нет, поэтому `PYTHONPATH=src` задаётся вручную. `tests/.env` существует, но автоматически не загружается — тесты не должны требовать БД или `settings`.