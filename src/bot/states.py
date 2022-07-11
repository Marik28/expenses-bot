from aiogram.dispatcher.filters.state import (
    StatesGroup,
    State,
)


class AddCategoryStates(StatesGroup):
    enter_category_name = State()


class AddExpenseStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_date = State()
