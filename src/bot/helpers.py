from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.callback_data import CallbackData

from .services.categories import CategoriesService

categories_cb = CallbackData("ctgr", "id")
add_expense_options_cb = CallbackData("exp", "action")
operation_type_cb = CallbackData("op", "type")


def get_categories_buttons(service: CategoriesService) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    categories = service.get_list()
    for category in categories:
        keyboard.insert(
            InlineKeyboardButton(
                category.name,
                callback_data=categories_cb.new(id=category.id),
            ),
        )
    return keyboard


def get_operation_types() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("Доход", callback_data=operation_type_cb.new(type="revenue")),
        InlineKeyboardButton("Расход", callback_data=operation_type_cb.new(type="expense")),
    )
    return keyboard


def get_add_expense_options() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(
            "Добавить комментарий",
            callback_data=add_expense_options_cb.new(action="comment"),
        ),
        InlineKeyboardButton(
            "Добавить дату",
            callback_data=add_expense_options_cb.new(action="date"),
        ),
        InlineKeyboardButton(
            "Выбрать категорию",
            callback_data=add_expense_options_cb.new(action="category"),
        ),
    )
    return keyboard
