import datetime as dt
from decimal import Decimal

from .base import BaseService
from ..db.models import Expense


class ExpensesService(BaseService):
    def add(self,
            amount: Decimal,
            is_expense: bool,
            user_id: int,
            category_id: int,
            comment: str = None,
            date: dt.date = None):
        expense = Expense()
        expense.amount = amount
        expense.is_expense = is_expense
        expense.date = date if date is not None else dt.date.today()
        expense.user_id = user_id
        expense.category_id = category_id
        expense.comment = comment
        self._save(expense)
