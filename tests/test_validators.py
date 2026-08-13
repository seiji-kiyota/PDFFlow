"""pdf_flow.validators のテスト。"""

import pytest

from pdf_flow.validators import is_pdf_file


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("invoice.pdf", True),
        ("invoice.PDF", True),
        ("invoice.xlsx", False),
        ("invoice", False),
    ],
)
def test_is_pdf_file(filename: str, expected: bool) -> None:
    """is_pdf_file() が拡張子を大文字小文字を問わず判定できること。"""
    assert is_pdf_file(filename) is expected
