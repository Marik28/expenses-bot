import re
from decimal import Decimal

import pytest

from bot.utils.parsing import EXPENSE_REGEX, parse_expense


@pytest.fixture(scope="session")
def compiled_regex():
    return re.compile(EXPENSE_REGEX)


@pytest.mark.parametrize(
    ["input_string", "expected_amount", "expected_comment"],
    [
        ("12378", "12378", None),
        ("1236,321", "1236,321", None),
        ("1236,321  ", "1236,321", None),
        ("1236,321  some comment", "1236,321", "some comment"),
    ],
)
def test_expense_regex_success(input_string, expected_amount, expected_comment, compiled_regex):
    result = compiled_regex.match(input_string)
    assert result is not None
    assert result.group("amount") == expected_amount
    assert result.group("comment") == expected_comment


@pytest.mark.parametrize(
    ["input_string", "expected"],
    [
        ("1238.312", (Decimal("1238.312"), None)),
        ("9421,1942", (Decimal("9421.1942"), None)),
        ("9421,1942   ", (Decimal("9421.1942"), None)),
        ("100 хлеб", (Decimal("100"), "хлеб")),
        ("1000 хлеб и вода", (Decimal("1000"), "хлеб и вода")),
    ],
)
def test_parse_expense(input_string, expected):
    assert parse_expense(input_string) == expected
