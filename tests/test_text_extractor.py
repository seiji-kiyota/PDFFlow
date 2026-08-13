"""pdf_flow.text_extractor のテスト。"""

from collections.abc import Callable

import pytest

from pdf_flow.text_extractor import extract_pdf_text


def test_extract_single_page_text(make_pdf_with_texts: Callable[[list[str]], bytes]) -> None:
    """1ページPDFから指定文字列を抽出できること。"""
    data = make_pdf_with_texts(["INVOICE-ALPHA"])
    result = extract_pdf_text("invoice.pdf", data)

    assert result.filename == "invoice.pdf"
    assert result.page_count == 1
    assert result.pages[0].page_number == 1
    assert "INVOICE-ALPHA" in result.pages[0].text
    assert "INVOICE-ALPHA" in result.full_text


def test_extract_multiple_pages_preserves_order(
    make_pdf_with_texts: Callable[[list[str]], bytes],
) -> None:
    """複数ページPDFのページ数・順序・各ページテキストを取得できること。"""
    data = make_pdf_with_texts(["PAGE-ONE", "PAGE-TWO", "PAGE-THREE"])
    result = extract_pdf_text("invoice.pdf", data)

    assert result.page_count == 3
    assert [page.page_number for page in result.pages] == [1, 2, 3]
    assert "PAGE-ONE" in result.pages[0].text
    assert "PAGE-TWO" in result.pages[1].text
    assert "PAGE-THREE" in result.pages[2].text
    assert result.full_text.find("PAGE-ONE") < result.full_text.find("PAGE-TWO")
    assert result.full_text.find("PAGE-TWO") < result.full_text.find("PAGE-THREE")


def test_extract_empty_page_does_not_fail(
    make_pdf_with_texts: Callable[[list[str]], bytes],
) -> None:
    """空ページが含まれていても処理が失敗しないこと。"""
    data = make_pdf_with_texts(["PAGE-ONE", "", "PAGE-THREE"])
    result = extract_pdf_text("invoice.pdf", data)

    assert result.page_count == 3
    assert "PAGE-ONE" in result.pages[0].text
    assert result.pages[1].text.strip() == ""
    assert "PAGE-THREE" in result.pages[2].text


def test_extract_pdf_without_text(make_pdf_bytes: Callable[[int], bytes]) -> None:
    """文字情報がない正常PDFを安全に扱えること。"""
    data = make_pdf_bytes(1)
    result = extract_pdf_text("blank.pdf", data)

    assert result.page_count == 1
    assert result.full_text.strip() == ""
    assert result.has_text() is False


def test_extract_invalid_pdf_raises_value_error() -> None:
    """不正なPDFデータでも未処理例外で停止しないこと。"""
    with pytest.raises(ValueError):
        extract_pdf_text("broken.pdf", b"not a pdf")
