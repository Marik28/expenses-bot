import datetime as dt
from decimal import Decimal
from io import BytesIO

import pandas as pd
from aiogram.types import (
    InputMediaPhoto,
    InputFile,
    MediaGroup,
    ParseMode,
)
from aiogram.utils.markdown import code
from sqlalchemy.orm import (
    Query,
    Load,
)

from .base import BaseService
from ..db.models import (
    Expense,
    Category,
)
from ..models.expenses import DailyStatistics
from ..settings import settings


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

    def _get_daily_stats_query(self, user_id: int, day: dt.date) -> Query:
        return (self.session.query(Expense, Category)
                .options(Load(Expense).load_only("id", "amount", "comment"),
                         Load(Category).defer("id").load_only("name"))
                .join(Category)
                .filter(Expense.date == day)
                .filter(Expense.is_expense.is_(True))
                .filter(Expense.user_id == user_id)
                .filter(Category.id.not_in(settings.exclude_categories)))

    def _make_plot(self,
                   df: pd.DataFrame,
                   plot_type: str,
                   caption=None,
                   parse_mode=None,
                   **plot_kwargs) -> InputMediaPhoto:
        buffer = BytesIO()
        getattr(df.plot, plot_type)(**plot_kwargs).figure.savefig(buffer)
        buffer.seek(0)
        return InputMediaPhoto(InputFile(buffer), caption=caption, parse_mode=parse_mode)

    def get_daily_statistics(self, user_id: int, day: dt.date) -> DailyStatistics | None:
        query = self._get_daily_stats_query(user_id, day)
        df = pd.read_sql(query.statement, self.session.bind, index_col="id")

        if df.empty:
            return None

        df["amount"] = -df["amount"]
        df.rename(columns={"name": "category"}, inplace=True)
        df = df.sort_values(by=["amount"], ascending=False)
        df = df[["amount", "category", "comment"]]
        df.index = range(len(df))

        agg_df = df.groupby("category").sum()
        agg_df = agg_df.sort_values(by="amount", ascending=False)
        pie = self._make_plot(agg_df, "pie", caption=code(agg_df.to_string()), parse_mode=ParseMode.MARKDOWN_V2,
                              y="amount", autopct="%.2f")
        bar = self._make_plot(agg_df, "bar")

        df.loc["Total"] = df.sum(numeric_only=True)
        df.fillna("-", inplace=True)
        return DailyStatistics(details=df.to_string(), aggregated=agg_df.to_string(), charts=MediaGroup([pie, bar]))
