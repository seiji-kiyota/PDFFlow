"""pdf_flow.validators のテスト。"""

from collections.abc import Callable

import pytest

from pdf_flow.validators import is_pdf_file, validate_pdf


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


def test_validate_pdf_accepts_lowercase_extension(
    make_pdf_bytes: Callable[[int], bytes],
) -> None:
    """拡張子 .pdf の正常なPDFを有効と判定すること。"""
    result = validate_pdf("invoice.pdf", make_pdf_bytes(1))
    assert result.ok is True
    assert result.error is None


def test_validate_pdf_accepts_uppercase_extension(
    make_pdf_bytes: Callable[[int], bytes],
) -> None:
    """拡張子 .PDF の正常なPDFを有効と判定すること。"""
    result = validate_pdf("invoice.PDF", make_pdf_bytes(1))
    assert result.ok is True
    assert result.error is None


def test_validate_pdf_rejects_non_pdf_extension(
    make_pdf_bytes: Callable[[int], bytes],
) -> None:
    """PDF以外の拡張子を無効と判定すること。"""
    result = validate_pdf("invoice.xlsx", make_pdf_bytes(1))
    assert result.ok is False
    assert result.error is not None


def test_validate_pdf_rejects_empty_file() -> None:
    """空ファイルを無効と判定すること。"""
    result = validate_pdf("invoice.pdf", b"")
    assert result.ok is False
    assert result.error is not None


def test_validate_pdf_rejects_corrupt_file() -> None:
    """破損したPDFデータを無効と判定すること。"""
    result = validate_pdf("invoice.pdf", b"not a pdf")
    assert result.ok is False
    assert result.error is not None


def test_validate_pdf_rejects_zero_page_pdf(
    make_pdf_bytes: Callable[[int], bytes],
) -> None:
    """ページ数が0のPDFを無効と判定すること。"""
    result = validate_pdf("invoice.pdf", make_pdf_bytes(0))
    assert result.ok is False
    assert result.error is not None
