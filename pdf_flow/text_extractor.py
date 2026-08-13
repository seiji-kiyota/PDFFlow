"""PDF本文テキスト抽出モジュール。

請求書PDFからページ単位の文字情報を取得する。
取引先名や金額などの項目解析は行わない。
"""

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True)
class PdfPageText:
    """1ページ分の抽出テキスト。"""

    page_number: int
    text: str


@dataclass(frozen=True)
class PdfTextExtraction:
    """PDF全体のテキスト抽出結果。"""

    filename: str
    page_count: int
    pages: tuple[PdfPageText, ...]
    full_text: str

    def has_text(self) -> bool:
        """抽出テキストが1文字以上あるかを返す。"""
        return any(page.text.strip() for page in self.pages)


def extract_pdf_text(filename: str, data: bytes) -> PdfTextExtraction:
    """PDFバイト列から本文テキストをページ単位で抽出する。

    空ページは空文字列として扱い、処理を継続する。
    ページ単位の抽出に失敗した場合も、そのページを空文字として継続する。

    Args:
        filename: 元ファイル名。
        data: PDFのバイト列。

    Returns:
        ファイル名、ページ数、ページ単位テキスト、全文を含む抽出結果。

    Raises:
        ValueError: PDFを開けない、または抽出処理に失敗した場合。
    """
    try:
        reader = PdfReader(BytesIO(data))
        pages: list[PdfPageText] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(PdfPageText(page_number=index, text=text))
    except Exception as exc:
        raise ValueError("PDFのテキストを抽出できませんでした。") from exc

    return PdfTextExtraction(
        filename=filename,
        page_count=len(pages),
        pages=tuple(pages),
        full_text="\n".join(page.text for page in pages),
    )
