"""PDF読込モジュール。

請求書PDFの取込および基本情報の取得を担当する。
本文の文字抽出や請求書項目の解析は行わない。
"""

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from pdf_flow.validators import validate_pdf


@dataclass(frozen=True)
class PdfFileInfo:
    """PDFファイルの基本情報。"""

    filename: str
    size_bytes: int
    page_count: int


def load_pdf_info(filename: str, data: bytes) -> PdfFileInfo:
    """PDFバイト列から基本情報を取得する。

    Args:
        filename: 元ファイル名。
        data: PDFのバイト列。

    Returns:
        ファイル名、サイズ、ページ数を含む基本情報。

    Raises:
        ValueError: PDFとして読み込めない場合。
    """
    result = validate_pdf(filename, data)
    if not result.ok:
        raise ValueError(result.error)

    reader = PdfReader(BytesIO(data))
    return PdfFileInfo(
        filename=filename,
        size_bytes=len(data),
        page_count=len(reader.pages),
    )
