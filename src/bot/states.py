from aiogram.dispatcher.filters.state import (
    StatesGroup,
    State,
)


class AddCategoryStates(StatesGroup):
    enter_category_name = State()


class AddExpenseStates(StatesGroup):
    waiting_for_comment = State()


class GetDailyStatistics(StatesGroup):
    waiting_for_date = State()


class GetPeriodStatistics(StatesGroup):
    waiting_for_date_from = State()
    waiting_for_date_to = State()
