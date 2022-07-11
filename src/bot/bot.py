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
    if not update.message:
        return

    await bot.send_message(update.message.chat.id, f"Произошла ошибка {str(error)}")
    state = dp.current_state(chat=update.message.chat.id, user=update.message.from_user.id)
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
    await message.answer(str(service.get_balance(message.from_user.id)))


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
    await query.answer(f"Выбрано {callback_data['type']}")
    async with state.proxy() as data:
        data["is_expense"] = callback_data["type"] == "expense"
    await query.message.answer(
        "Выберите действие",
        reply_markup=get_add_expense_options(),
    )


@dp.callback_query_handler(add_expense_options_cb.filter(action="date"), state="*")
async def add_date(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Введите дату")
    await AddExpenseStates.waiting_for_date.set()
    await query.message.answer("Введите дату в формате 'dd.mm.yy'")


@dp.message_handler(state=AddExpenseStates.waiting_for_date)
async def parse_date(message: types.Message, state: FSMContext):
    try:
        date = dt.datetime.strptime(message.text, "%d.%m.%y").date()
    except ValueError:
        await message.answer("Неверный формат")
        return

    await message.answer("Дата сохранена")

    async with state.proxy() as data:
        data["date"] = date

    await state.reset_state(with_data=False)


@dp.callback_query_handler(add_expense_options_cb.filter(action="comment"), state="*")
async def add_comment(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Введите текст комментария")
    await AddExpenseStates.waiting_for_comment.set()
    await query.message.answer("Введите текст комментария")


@dp.message_handler(state=AddExpenseStates.waiting_for_comment)
async def parse_comment(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["comment"] = message.text

    await message.answer("Комментарий сохранен")
    await state.reset_state(with_data=False)


@dp.callback_query_handler(add_expense_options_cb.filter(action="category"), state="*")
async def show_categories(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    service = CategoriesService(Session())
    await query.answer("Выберите категорию")
    await query.message.answer("Выберите категорию",
                               reply_markup=get_categories_buttons(service))
    await state.reset_state(with_data=False)


@dp.callback_query_handler(categories_cb.filter(), state="*")
async def save_expense(query: types.CallbackQuery, state: FSMContext, callback_data: dict):
    await query.answer("Категория выбрана")
    service = ExpensesService(Session())
    async with state.proxy() as data:
        service.add(
            amount=data["amount"],
            is_expense=data["is_expense"],
            user_id=query.from_user.id,
            category_id=callback_data["id"],
            comment=data.get("comment"),
            date=data.get("date"),
        )
    await query.message.answer("Данные сохранены")
    await state.finish()
