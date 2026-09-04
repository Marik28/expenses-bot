import datetime as dt
from decimal import Decimal
from enum import Enum
from io import BytesIO

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.figure import Figure
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
from ..models.expenses import (
    CategoryMonthStatistics,
    CategoryTrendStatistics,
    DailyStatistics,
    PeriodStatistics,
)
from ..settings import settings
from ..utils.datetime import localnow, month_bounds, month_label


class ChartColor(str, Enum):
    """Палитра графиков статистики, подобранная под чтение с телефона."""

    ACCENT = "#2a78d6"
    """Столбцы."""
    MEAN_LINE = "#eb6834"
    """Пунктир среднего."""
    INK = "#1a1a19"
    """Основной текст."""
    MUTED = "#52514e"
    """Подписи осей."""
    EDGE = "#d5d4cf"
    """Рамка осей."""
    GRID = "#e9e8e3"
    """Сетка."""


def configure_matplotlib() -> None:
    """Одноразовая настройка matplotlib для графиков статистики.

    Дёргается при старте бота (``__main__.on_startup``): бэкенд без дисплея плюс
    общая типографика — крупный шрифт, спокойная светлая сетка.
    """
    matplotlib.use("Agg")
    plt.rcParams.update({
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 13,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.titlepad": 12,
        "axes.labelcolor": ChartColor.MUTED.value,
        "axes.edgecolor": ChartColor.EDGE.value,
        "text.color": ChartColor.INK.value,
        "xtick.color": ChartColor.MUTED.value,
        "ytick.color": ChartColor.MUTED.value,
        "axes.grid": True,
        "grid.color": ChartColor.GRID.value,
        "grid.linewidth": 0.8,
    })


def _fmt_kzt(value: float) -> str:
    """1234567 -> '1 234 567' (пробел как разделитель разрядов)."""
    return f"{value:,.0f}".replace(",", " ")


def _fmt_kzt_short(value: float) -> str:
    """Компактная подпись суммы для тесных мест: 1234567 -> '1.2 млн', 42800 -> '43 тыс'."""
    v = abs(float(value))
    if v >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if v >= 10_000:
        return f"{value / 1_000:.0f} тыс"
    if v >= 1_000:
        return f"{value / 1_000:.1f} тыс"
    return f"{value:.0f}"


def _period_label(date_from: dt.date, date_to: dt.date) -> str:
    d1 = pd.Timestamp(date_from).strftime("%d.%m.%Y")
    d2 = pd.Timestamp(date_to).strftime("%d.%m.%Y")
    return d1 if d1 == d2 else f"{d1} – {d2}"


class ExpensesService(BaseService):
    def add(
            self,
            amount: Decimal,
            is_expense: bool,
            user_id: int,
            category_id: int,
            comment: str = None,
            date: dt.date = None
    ) -> Expense:
        expense = Expense()
        expense.amount = amount
        expense.is_expense = is_expense
        expense.date = date if date is not None else localnow().date()
        expense.user_id = user_id
        expense.category_id = category_id
        expense.comment = comment
        self._save(expense)
        return expense

    def _get_daily_stats_query(self, user_id: int, day: dt.date) -> Query:
        return (self.session.query(Expense, Category)
                .options(Load(Expense).load_only("id", "amount", "comment"),
                         Load(Category).defer("id").load_only("name"))
                .join(Category)
                .filter(Expense.date == day)
                .filter(Expense.is_expense.is_(True))
                .filter(Expense.user_id == user_id)
                .filter(Category.id.not_in(settings.exclude_categories)))

    @staticmethod
    def _render(fig: Figure, caption: str | None = None,
                parse_mode: str | None = None) -> InputMediaPhoto:
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        return InputMediaPhoto(InputFile(buffer), caption=caption, parse_mode=parse_mode)

    def _make_plot(self,
                   df: pd.DataFrame,
                   plot_type: str,
                   caption=None,
                   parse_mode=None,
                   **plot_kwargs) -> InputMediaPhoto:
        fig, ax = plt.subplots(figsize=(7, 6))
        getattr(df.plot, plot_type)(ax=ax, **plot_kwargs)
        if plot_type != "pie":
            ax.tick_params(axis="x", rotation=30)
        return self._render(fig, caption, parse_mode)

    def _barh_chart(self, amounts: pd.Series, title: str) -> InputMediaPhoto:
        """Горизонтальные столбцы: подписи читаются без наклона, рядом с каждым
        столбцом — сумма. ``amounts.index`` — готовые подписи."""
        amounts = amounts.sort_values()
        # высота растёт с числом столбцов, чтобы подписи не слипались
        height = max(2.8, 0.52 * len(amounts) + 1.4)
        fig, ax = plt.subplots(figsize=(7.5, height))

        bars = ax.barh(amounts.index.astype(str), amounts.to_numpy(),
                       color=ChartColor.ACCENT.value, height=0.62)
        # каждый столбец подписан суммой — ось X с делениями не нужна
        ax.bar_label(bars, labels=[f"  {_fmt_kzt(v)} ₸" for v in amounts.to_numpy()],
                     padding=1, fontsize=12, color=ChartColor.INK.value)

        ax.set_title(title)
        ax.margins(x=0.24)
        ax.xaxis.set_visible(False)
        ax.grid(visible=False)
        for side in ("top", "right", "bottom"):
            ax.spines[side].set_visible(False)
        ax.set_axisbelow(True)
        return self._render(fig)

    def _category_chart(self, amounts: pd.Series, date_from: dt.date,
                        date_to: dt.date) -> InputMediaPhoto:
        """Горизонтальные столбцы по категориям за период."""
        title = (f"Расходы по категориям\n{_period_label(date_from, date_to)} "
                 f"· всего {_fmt_kzt(float(amounts.sum()))} ₸")
        return self._barh_chart(amounts, title)

    def _daily_trend_chart(self, amounts: pd.Series, date_from: dt.date,
                           date_to: dt.date) -> InputMediaPhoto:
        """Расходы во времени: непрерывная ось дат (промежутки без трат — нули),
        пунктир среднего. Длинные периоды агрегируются по неделям, чтобы столбцы
        не сливались на экране телефона."""
        idx = pd.date_range(pd.Timestamp(date_from).normalize(),
                            pd.Timestamp(date_to).normalize(), freq="D")
        series = amounts.copy()
        series.index = pd.to_datetime(series.index)
        series = series.reindex(idx, fill_value=0)
        total = float(series.sum())

        days = len(idx)
        if days > 92:
            series = series.resample("W-MON", label="left").sum()
            bar_width, unit, noun = 5.5, "в неделю", "по неделям"
        else:
            bar_width, unit, noun = 0.85, "в день", "по дням"

        nonzero = series[series > 0]
        mean = float(nonzero.mean()) if not nonzero.empty else 0.0

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(series.index, series.to_numpy(), color=ChartColor.ACCENT.value, width=bar_width)

        if mean:
            ax.axhline(mean, color=ChartColor.MEAN_LINE.value, linestyle="--", linewidth=1.6,
                       label=f"среднее {unit} · {_fmt_kzt(mean)} ₸")
            ax.legend(loc="upper left", frameon=False, fontsize=11)

        ax.set_title(f"Расходы {noun}\n{_period_label(date_from, date_to)} "
                     f"· всего {_fmt_kzt(total)} ₸")
        peak = float(series.max()) if len(series) else 0.0
        ax.set_ylim(0, peak * 1.18 if peak else 1)
        ax.set_xlim(idx[0] - pd.Timedelta(days=1), idx[-1] + pd.Timedelta(days=1))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _fmt_kzt(v)))
        if days <= 16:
            ax.xaxis.set_major_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.tick_params(axis="x", rotation=0)
        ax.grid(axis="x", visible=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_axisbelow(True)
        return self._render(fig)

    def _monthly_trend_chart(self, monthly: pd.Series, category: Category) -> InputMediaPhoto:
        """Столбцы трат по месяцам за последний год по одной категории.

        Линия тренда — скользящее среднее за 3 месяца, посчитанное только по
        завершённым месяцам; текущий (неполный) месяц из линии исключён, его
        столбец показан приглушённым."""
        values = monthly.to_numpy(dtype=float)
        n = len(monthly)
        positions = list(range(n))
        labels = [p.strftime("%m.%y") for p in monthly.index]
        labels[-1] += "\n(неполн.)"

        total = float(monthly.sum())
        nonzero = monthly[monthly > 0]
        mean = float(nonzero.mean()) if not nonzero.empty else 0.0

        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(positions, values, color=ChartColor.ACCENT.value, width=0.6)
        bars[-1].set_alpha(0.3)

        ax.bar_label(bars, labels=[_fmt_kzt_short(v) if v else "" for v in values],
                     padding=4, fontsize=8, rotation=90, color=ChartColor.MUTED.value)

        # скользящее среднее за 3 месяца по завершённым месяцам
        completed = monthly.iloc[:-1]
        if (completed > 0).any():
            ma = completed.rolling(3, min_periods=1).mean().to_numpy(dtype=float)
            ax.plot(positions[:-1], ma, color=ChartColor.MEAN_LINE.value, linewidth=2.4,
                    marker="o", markersize=4, label="скользящее среднее, 3 мес")

        if mean:
            ax.axhline(mean, color=ChartColor.MUTED.value, linestyle="--", linewidth=1.2,
                       label=f"среднее за месяц · {_fmt_kzt(mean)} ₸")

        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="upper left", frameon=False, fontsize=10)

        ax.set_title(f"«{category.name}» — траты по месяцам\n"
                     f"{labels[0]} – {monthly.index[-1].strftime('%m.%y')} "
                     f"· всего {_fmt_kzt(total)} ₸")
        peak = float(values.max()) if n else 0.0
        ax.set_ylim(0, peak * 1.32 if peak else 1)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=9)
        ax.tick_params(axis="x", rotation=45)
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment("right")
        ax.margins(x=0.02)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _fmt_kzt(v)))
        ax.grid(axis="x", visible=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_axisbelow(True)
        return self._render(fig)

    def get_category_monthly_trend(self, user_id: int, category_id: int,
                                   months: int = 12) -> CategoryTrendStatistics | None:
        category = self.session.get(Category, category_id)
        if category is None:
            return None

        start_period = pd.Period(localnow().date(), freq="M") - (months - 1)
        today = localnow().date()
        query = (self.session.query(Expense)
                 .options(Load(Expense).load_only("id", "date", "amount"))
                 .filter(Expense.date >= start_period.start_time.date())
                 .filter(Expense.date <= today)
                 .filter(Expense.is_expense.is_(True))
                 .filter(Expense.user_id == user_id)
                 .filter(Expense.category_id == category_id))

        df = pd.read_sql(query.statement, self.session.bind, index_col="id")
        if df.empty:
            return None

        df["amount"] = -df["amount"]
        df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")
        monthly = df.groupby("month")["amount"].sum()
        full_idx = pd.period_range(start_period, periods=months, freq="M")
        monthly = monthly.reindex(full_idx, fill_value=0)

        chart = self._monthly_trend_chart(monthly, category)
        return CategoryTrendStatistics(charts=MediaGroup([chart]))

    def get_category_month_statistics(self, user_id: int, category_id: int,
                                      month: dt.date) -> CategoryMonthStatistics | None:
        category = self.session.get(Category, category_id)
        if category is None:
            return None

        date_from, date_to = month_bounds(month)
        query = (self.session.query(Expense)
                 .options(Load(Expense).load_only("id", "date", "amount", "comment"))
                 .filter(Expense.date.between(date_from, date_to))
                 .filter(Expense.is_expense.is_(True))
                 .filter(Expense.user_id == user_id)
                 .filter(Expense.category_id == category_id))

        df = pd.read_sql(query.statement, self.session.bind, index_col="id")
        if df.empty:
            return None

        df["amount"] = -df["amount"]
        df["date"] = pd.to_datetime(df["date"])
        title = month_label(month)
        total = float(df["amount"].sum())

        # график 1 — траты по дням месяца
        daily = df.groupby(df["date"].dt.normalize())["amount"].sum()
        charts = [self._daily_trend_chart(daily, date_from, date_to)]

        # график 2 — разбивка по комментариям, если их несколько
        by_comment = (df.assign(comment=df["comment"].fillna("—"))
                      .groupby("comment")["amount"].sum())
        if len(by_comment) >= 2:
            by_comment.index = [c if len(c) <= 23 else c[:22] + "…" for c in by_comment.index]
            comment_title = (f"«{category.name}» — по комментариям\n"
                             f"{title} · всего {_fmt_kzt(total)} ₸")
            charts.append(self._barh_chart(by_comment, comment_title))

        # текстовый список трат
        listing = df[["date", "amount", "comment"]].copy()
        listing["date"] = listing["date"].dt.strftime("%d.%m")
        listing["comment"] = listing["comment"].fillna("—")
        listing.sort_values(by="amount", ascending=False, inplace=True)
        listing.rename(columns={"date": "дата", "amount": "сумма", "comment": "комментарий"},
                       inplace=True)
        listing.index = range(1, len(listing) + 1)
        listing.loc["Итого"] = ["", listing["сумма"].sum(), ""]
        details = f"«{category.name}» — {title}\n\n{listing.to_string()}"

        return CategoryMonthStatistics(details=details, charts=MediaGroup(charts))

    def get_daily_statistics(self, user_id: int, day: dt.date) -> DailyStatistics | None:
        query = self._get_daily_stats_query(user_id, day)
        df = pd.read_sql(query.statement, self.session.bind, index_col="id")

        if df.empty:
            return None

        df["amount"] = -df["amount"]
        df.rename(columns={"name": "category"}, inplace=True)
        df = df.sort_values(by=["amount"], ascending=False)
        df = df[["amount", "category", "comment"]]
        df.index = range(1, len(df) + 1)

        agg_df = df.groupby("category").sum()
        agg_df = agg_df.sort_values(by="amount", ascending=False)
        pie = self._make_plot(agg_df, "pie", caption=code(agg_df.to_string()), parse_mode=ParseMode.MARKDOWN_V2,
                              y="amount", autopct="%.2f")
        bar = self._make_plot(agg_df, "bar")

        df.loc["Total"] = df.sum(numeric_only=True)
        df.fillna("-", inplace=True)
        return DailyStatistics(details=df.to_string(), aggregated=agg_df.to_string(), charts=MediaGroup([pie, bar]))

    def get_period_statistics(self, user_id: int, date_from: dt.date, date_to: dt.date) -> PeriodStatistics | None:
        query = (self.session.query(Expense, Category)
                 .options(Load(Expense).load_only("id", "date", "amount", "comment"),
                          Load(Category).defer("id").load_only("name"))
                 .join(Category)
                 .filter(Expense.date.between(date_from, date_to))
                 .filter(Expense.is_expense.is_(True))
                 .filter(Expense.user_id == user_id)
                 .filter(Category.id.not_in(settings.exclude_categories)))

        df = pd.read_sql(query.statement, query.session.bind, index_col="id")

        if df.empty:
            return None

        df.rename(columns={"name": "category"}, inplace=True)
        df["amount"] = -df["amount"]
        df = df[["date", "amount", "category", "comment"]]
        df.sort_values(by=["date", "amount"], ascending=[True, False], inplace=True)
        df.index = range(1, len(df) + 1)

        top_ten_expenses_df = df.sort_values(by=["amount"], ascending=False).head(10)

        daily_df = df.groupby(by="date").sum(numeric_only=True)
        cat_df = df.groupby(by="category").sum(numeric_only=True)

        category_chart = self._category_chart(cat_df["amount"], date_from, date_to)
        trend_chart = self._daily_trend_chart(daily_df["amount"], date_from, date_to)

        return PeriodStatistics(top_ten=top_ten_expenses_df.to_string(index=False),
                                daily=daily_df.to_string(index=False),
                                charts=MediaGroup([category_chart, trend_chart]))
