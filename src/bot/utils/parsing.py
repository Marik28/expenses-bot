from decimal import Decimal

EXPENSE_REGEX = r"^(?P<amount>\d{1,10}([,|.]\d*)?)\s*(?P<comment>.+)?$"


def parse_expense(msg_text: str) -> tuple[Decimal, str | None]:
    amount, _, comment = msg_text.partition(" ")
    comment = comment.strip()

    if not comment:
        comment = None

    return Decimal(amount.replace(",", ".")), comment
