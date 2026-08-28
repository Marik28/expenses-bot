from decimal import Decimal

import pytest

from bot.utils.parsing import EXPENSE_REGEX, ParsedExpense, parse_expense


@pytest.mark.parametrize(
    ["input_string", "expected_amount", "expected_comment"],
    [
        ("12378", "12378", None),
        ("1236,321", "1236,321", None),
        ("1236,321  ", "1236,321", None),
        ("1236,321  some comment", "1236,321", "some comment"),
    ],
)
def test_expense_regex_success(input_string, expected_amount, expected_comment):
    result = EXPENSE_REGEX.match(input_string)
    assert result is not None
    assert result.group("amount") == expected_amount
    assert result.group("comment") == expected_comment


@pytest.mark.parametrize(
    ["input_string", "expected"],
    [
        # без валюты — базовая KZT
        ("1238.312", ParsedExpense(Decimal("1238.312"), "KZT", None)),
        ("9421,1942", ParsedExpense(Decimal("9421.1942"), "KZT", None)),
        ("9421,1942   ", ParsedExpense(Decimal("9421.1942"), "KZT", None)),
        ("100 хлеб", ParsedExpense(Decimal("100"), "KZT", "хлеб")),
        ("1000 хлеб и вода", ParsedExpense(Decimal("1000"), "KZT", "хлеб и вода")),
        # код валюты слитно — суффикс
        ("50USD подписка", ParsedExpense(Decimal("50"), "USD", "подписка")),
        ("100usd хлеб", ParsedExpense(Decimal("100"), "USD", "хлеб")),
        ("100usd", ParsedExpense(Decimal("100"), "USD", None)),
        ("100.5usd", ParsedExpense(Decimal("100.5"), "USD", None)),
        # код через пробел валютой НЕ считается — уходит в комментарий
        ("50 USD подписка", ParsedExpense(Decimal("50"), "KZT", "USD подписка")),
        ("100 usd", ParsedExpense(Decimal("100"), "KZT", "usd")),
        # обычный текст-комментарий
        ("100 car wash", ParsedExpense(Decimal("100"), "KZT", "car wash")),
        # слитный комментарий без пробела (не 3 латинские буквы) — не валюта
        ("100хлеб", ParsedExpense(Decimal("100"), "KZT", "хлеб")),
        ("50кг", ParsedExpense(Decimal("50"), "KZT", "кг")),
        ("100usdx", ParsedExpense(Decimal("100"), "KZT", "usdx")),
    ],
)
def test_parse_expense(input_string, expected):
    assert parse_expense(input_string) == expected
