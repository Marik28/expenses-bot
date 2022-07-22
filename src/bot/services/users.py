import datetime as dt
from decimal import Decimal

from sqlalchemy import func

from .base import BaseService
from ..db.models import (
    User,
    Expense,
)
from ..settings import settings


class UsersService(BaseService):
    def create(self, user_id: int, username: str | None):
        user = User()
        user.id = user_id
        user.username = username
        self._save(user)

    def _get(self, user_id: int) -> User | None:
        return self.session.query(User).filter(User.id == user_id).first()

    def get_balance(self, user_id: int) -> Decimal:
        return self._get(user_id).balance

    def get_daily_expenses(self, user_id: int, day: dt.date) -> Decimal:
        return (self.session
                .query(func.sum(Expense.amount))
                .filter(Expense.is_expense.is_(True))
                .filter(Expense.date == day)
                .filter(Expense.user_id == user_id)
                .filter(Expense.category_id.not_in(settings.exclude_categories))  # долги не считаем
                .one())[0] or Decimal('0.0')
