"""テスト共通fixture。"""

from collections.abc import Callable
from io import BytesIO

import pytest
from pypdf import PdfWriter


@pytest.fixture
def make_pdf_bytes() -> Callable[[int], bytes]:
    """指定ページ数の最小PDFバイト列を生成する。"""

    def _make(page_count: int) -> bytes:
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    return _make
