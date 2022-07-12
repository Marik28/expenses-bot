from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Query

from .base import BaseService
from ..db.models import (
    User,
    Expense,
)


class UsersService(BaseService):
    def create(self, user_id: int, username: str | None):
        user = User()
        user.id = user_id
        user.username = username
        self._save(user)

    def _get_expenses(self, user_id: int, expenses: bool) -> Query:
        return (self.session
                .query(func.sum(Expense.amount))
                .select_from(User)
                .join(User.expenses)
                .filter(Expense.is_expense.is_(expenses))
                .filter(User.id == user_id))

    def get_balance(self, user_id: int) -> Decimal:
        q = (self.session
             .query(func.sum(Expense.amount))
             .select_from(User)
             .join(User.expenses)
             .filter(User.id == user_id))

        balance = q.one()[0]
        return balance
