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
        emoji_bit = f"{category.emoji} " if category.emoji else ""
        text = f"{emoji_bit}{category.name}"
        keyboard.insert(
            InlineKeyboardButton(
                text,
                callback_data=categories_cb.new(id=category.id),
            ),
        )
    return keyboard


def get_operation_types() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📈 Доход", callback_data=operation_type_cb.new(type="revenue")),
        InlineKeyboardButton("📉 Расход", callback_data=operation_type_cb.new(type="expense")),
    )
    return keyboard


def get_add_expense_options(*, with_save_btn: bool = False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    options = [("🗒 Изменить комментарий", "comment"),
               ("📅 Изменить дату", "date"),
               ("☕ Выбрать категорию", "category")]
    for text, action in options:
        keyboard.insert(InlineKeyboardButton(text, callback_data=add_expense_options_cb.new(action=action)))

    if with_save_btn:
        keyboard.insert(InlineKeyboardButton("💾 Сохранить", callback_data=add_expense_options_cb.new(action="save")))

    return keyboard
