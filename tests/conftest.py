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


@pytest.fixture
def make_pdf_with_texts() -> Callable[[list[str]], bytes]:
    """ページごとの文字列を埋め込んだ最小PDFを生成する。"""

    def _make(texts: list[str]) -> bytes:
        return _build_pdf_with_texts(texts)

    return _make


def _build_pdf_with_texts(texts: list[str]) -> bytes:
    """指定テキストを各ページに配置した最小PDFを組み立てる。"""
    if not texts:
        texts = [""]

    page_count = len(texts)
    font_id = 3 + page_count * 2
    objects: list[bytes] = []

    def add_object(object_id: int, payload: bytes) -> None:
        objects.append(
            f"{object_id} 0 obj\n".encode("ascii") + payload + b"\nendobj\n"
        )

    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(page_count))
    add_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    add_object(2, f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"))

    for index, text in enumerate(texts):
        page_id = 3 + index * 2
        content_id = 4 + index * 2
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if text:
            stream = f"BT /F1 12 Tf 72 200 Td ({escaped}) Tj ET\n"
        else:
            stream = "BT ET\n"
        stream_bytes = stream.encode("ascii")
        add_object(
            page_id,
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 400] "
                f"/Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            ).encode("ascii"),
        )
        add_object(
            content_id,
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"endstream",
        )

    add_object(font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    position = len(header)
    for obj in objects:
        offsets.append(position)
        position += len(obj)

    body = b"".join(objects)
    xref_lines = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n \n")
    xref = "".join(xref_lines).encode("ascii")
    trailer = (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{len(header) + len(body)}\n%%EOF\n"
    ).encode("ascii")
    return header + body + xref + trailer
