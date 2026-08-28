import dataclasses
import re
from decimal import Decimal

BASE_CURRENCY = "KZT"

EXPENSE_REGEX = re.compile(
    r"^(?P<amount>\d{1,10}([,|.]\d*)?)"
    r"(?P<cur>[A-Za-z]{3}(?=\s|$))?"
    r"\s*(?P<comment>\S.*?)?\s*$"
)


@dataclasses.dataclass(frozen=True)
class ParsedExpense:
    amount: Decimal
    currency: str
    comment: str | None

    @property
    def is_kzt(self) -> bool:
        return self.currency == BASE_CURRENCY


def parse_expense(msg_text: str) -> ParsedExpense:
    """Разбирает сообщение «[КОД]сумма[КОД] [комментарий]»."""
    match = EXPENSE_REGEX.match(msg_text)
    if match is None:
        raise ValueError(f"Не удалось распарсить расход: {msg_text!r}")

    amount = Decimal(match["amount"].replace(",", "."))
    currency = (match["cur"] or BASE_CURRENCY).upper()
    comment = (match["comment"] or "").strip() or None
    return ParsedExpense(amount=amount, currency=currency, comment=comment)
