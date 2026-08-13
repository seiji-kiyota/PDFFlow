"""入力PDFの検証モジュール。

アップロードされたファイルが処理対象として妥当かを判定する。
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def is_pdf_file(filename: str) -> bool:
    """ファイル名の拡張子がPDFかどうかを判定する。

    大文字・小文字は区別しない。パス付きのファイル名も受け付ける。

    Args:
        filename: 判定対象のファイル名またはパス。

    Returns:
        拡張子が ``.pdf`` の場合は True、それ以外は False。
    """
    return Path(filename).suffix.lower() == ".pdf"


@dataclass(frozen=True)
class PdfValidationResult:
    """PDF検証結果。"""

    ok: bool
    error: str | None = None


def validate_pdf(filename: str, data: bytes) -> PdfValidationResult:
    """PDFとして読み込めるかを検証する。

    次を順に確認する。

    - 拡張子が ``.pdf`` である（大文字・小文字は区別しない）
    - ファイルが空ではない
    - PDFライブラリで正常に開ける
    - ページ数が1ページ以上ある

    Args:
        filename: 判定対象のファイル名またはパス。
        data: ファイルのバイト列。

    Returns:
        検証結果。失敗時は ``error`` に理由を格納する。
    """
    if not is_pdf_file(filename):
        return PdfValidationResult(ok=False, error="PDFファイルではありません。")

    if not data:
        return PdfValidationResult(ok=False, error="ファイルが空です。")

    try:
        reader = PdfReader(BytesIO(data))
        page_count = len(reader.pages)
    except Exception:
        return PdfValidationResult(
            ok=False,
            error="PDFを開けません。ファイルが破損している可能性があります。",
        )

    if page_count < 1:
        return PdfValidationResult(ok=False, error="ページが含まれていないPDFです。")

    return PdfValidationResult(ok=True)
