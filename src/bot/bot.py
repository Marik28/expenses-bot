import datetime as dt
from decimal import Decimal

import sqlalchemy.exc
from aiogram import types
from aiogram.bot import Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import (
    Dispatcher,
    FSMContext,
)
from aiogram.types import ParseMode
from aiogram.utils.markdown import (
    spoiler,
    code,
)
from aiogram_calendar import (
    SimpleCalendar,
    simple_cal_callback,
)

from .db.database import Session
from .helpers import (
    get_add_expense_options,
    add_expense_options_cb,
    get_categories_buttons,
    categories_cb,
    operation_type_cb,
    get_operation_types,
)
from .services.categories import CategoriesService
from .services.expenses import ExpensesService
from .services.users import UsersService
from .settings import settings
from .states import (
    AddCategoryStates,
    AddExpenseStates,
)

bot = Bot(settings.telegram_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.errors_handler(exception=Exception)
async def handle_error(update: types.Update, error: Exception):
    message = update.message or update.callback_query.message
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    error_msg = code(error.__class__.__name__)
    await bot.send_message(state.chat, f"Произошла ошибка {error_msg}", parse_mode=ParseMode.MARKDOWN_V2)
    await state.finish()


@dp.message_handler(commands=["start"])
async def create_user(message: types.Message):
    service = UsersService(Session())

    try:
        service.create(message.from_user.id, message.from_user.username)
    except sqlalchemy.exc.IntegrityError:
        pass

    await message.answer("Дороу")


@dp.message_handler(commands=["help"])
async def greet(message: types.Message):
    await message.answer("Дороу")


@dp.message_handler(commands=["balance"])
async def get_balance(message: types.Message):
    service = UsersService(Session())
    balance = str(service.get_balance(message.from_user.id))
    await message.answer(spoiler(balance), parse_mode=ParseMode.MARKDOWN_V2)


@dp.message_handler(commands=["today"])
async def get_today_expenses(message: types.Message):
    service = UsersService(Session())
    date = dt.date.today()
    expenses = service.get_daily_expenses(message.from_user.id, date)
    await message.answer(spoiler(expenses), parse_mode=ParseMode.MARKDOWN_V2)


@dp.message_handler(commands=["cancel"], state="*")
async def cancel_state(message: types.Message, state: FSMContext):
    await state.reset_state(True)
    await state.finish()
    await message.answer("Действие отменено")


@dp.message_handler(commands=["add_category"])
async def process_add_category(message: types.Message):
    await AddCategoryStates.enter_category_name.set()
    await message.answer("Введите название категории")


@dp.message_handler(state=AddCategoryStates.enter_category_name)
async def add_category(message: types.Message, state: FSMContext):
    service = CategoriesService(Session())
    category = message.text.strip().capitalize()

    try:
        service.add(category)
    except sqlalchemy.exc.IntegrityError:
        await message.answer(f"Категория '{category}' уже существует")
    else:
        await message.answer(f"Категория '{category}' добавлена")
    finally:
        await state.reset_state(with_data=False)


@dp.message_handler(regexp=r"^\d{1,10}([,|.]\d*)?$")
async def process_add_expense(message: types.Message, state: FSMContext):
    amount = Decimal(message.text.replace(",", "."))
    async with state.proxy() as data:
        data["amount"] = abs(amount)
    await message.answer(
        "Доход или расход?",
        reply_markup=get_operation_types(),
    )


@dp.callback_query_handler(operation_type_cb.filter())
async def choose_operation_type(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer(f"Выбрано '{callback_data['type'].capitalize()}'")
    async with state.proxy() as data:
        data["is_expense"] = callback_data["type"] == "expense"

    await query.message.edit_text("Выберите действие:",
                                  reply_markup=get_add_expense_options(with_save_btn=data.get("can_save", False)))


@dp.callback_query_handler(add_expense_options_cb.filter(action="date"), state="*")
async def edit_date(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Введите дату")
    await query.message.edit_text("Введите дату в формате 'дд.мм.гг'",
                                  reply_markup=await SimpleCalendar().start_calendar())


# simple calendar usage
@dp.callback_query_handler(simple_cal_callback.filter())
async def process_date_selection(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    selected, date = await SimpleCalendar().process_selection(query, callback_data)

    if not selected:
        return

    async with state.proxy() as data:
        data["date"] = date

    await query.answer("Дата сохранена.")
    await query.message.edit_text(
        f'Дата сохранена. Выберите действие:',
        reply_markup=get_add_expense_options(with_save_btn=data.get("can_save", False))
    )


@dp.callback_query_handler(add_expense_options_cb.filter(action="comment"), state="*")
async def edit_comment(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Введите текст комментария")
    await AddExpenseStates.waiting_for_comment.set()
    await query.message.edit_text("Введите текст комментария", reply_markup=None)


@dp.message_handler(state=AddExpenseStates.waiting_for_comment)
async def parse_comment(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["comment"] = message.text

    await state.reset_state(with_data=False)
    await message.answer("Комментарий сохранен. Выберите действие",
                         reply_markup=get_add_expense_options(with_save_btn=data.get("can_save", False)))


@dp.callback_query_handler(add_expense_options_cb.filter(action="category"), state="*")
async def show_categories(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    service = CategoriesService(Session())
    await query.answer("Выберите категорию")
    await query.message.edit_text("Выберите категорию",
                                  reply_markup=get_categories_buttons(service))
    await state.reset_state(with_data=False)


@dp.callback_query_handler(categories_cb.filter(), state="*")
async def add_category(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Категория выбрана")
    async with state.proxy() as data:
        data["category_id"] = callback_data["id"]
        data["can_save"] = True

    await query.message.edit_text("Категория сохранена. Выберите действие:",
                                  # FIXME: повторяется везде
                                  reply_markup=get_add_expense_options(with_save_btn=data.get("can_save", False)))


# TODO: нельзя параллельно сохранять несколько записей
@dp.callback_query_handler(add_expense_options_cb.filter(action="save"), state="*")
async def save_expense(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    service = ExpensesService(Session())
    async with state.proxy() as data:
        service.add(
            amount=data["amount"] if not data["is_expense"] else -data["amount"],
            is_expense=data["is_expense"],
            user_id=query.from_user.id,
            category_id=data["category_id"],
            comment=data.get("comment"),
            date=data.get("date"),
        )

    await query.answer("Данные сохранены!")
    await query.message.edit_text("Данные сохранены!", reply_markup=None)
    await state.finish()
