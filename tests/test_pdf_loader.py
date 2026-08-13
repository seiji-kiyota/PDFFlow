"""pdf_flow.pdf_loader のテスト。"""

from collections.abc import Callable

import pytest

from pdf_flow.pdf_loader import load_pdf_info


def test_load_pdf_info_single_page(make_pdf_bytes: Callable[[int], bytes]) -> None:
    """正常な1ページPDFのページ数を取得できること。"""
    data = make_pdf_bytes(1)
    info = load_pdf_info("invoice.pdf", data)
    assert info.filename == "invoice.pdf"
    assert info.page_count == 1


def test_load_pdf_info_multiple_pages(make_pdf_bytes: Callable[[int], bytes]) -> None:
    """複数ページPDFのページ数を取得できること。"""
    data = make_pdf_bytes(3)
    info = load_pdf_info("invoice.pdf", data)
    assert info.page_count == 3


def test_load_pdf_info_file_size(make_pdf_bytes: Callable[[int], bytes]) -> None:
    """ファイルサイズを取得できること。"""
    data = make_pdf_bytes(1)
    info = load_pdf_info("invoice.pdf", data)
    assert info.size_bytes == len(data)
    assert info.size_bytes > 0


def test_load_pdf_info_rejects_invalid_data() -> None:
    """不正なPDFデータはValueErrorになること。"""
    with pytest.raises(ValueError):
        load_pdf_info("broken.pdf", b"not a pdf")
