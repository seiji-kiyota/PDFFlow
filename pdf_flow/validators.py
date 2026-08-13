"""入力PDFの検証モジュール。

アップロードされたファイルが処理対象として妥当かを判定する。
Phase 1では拡張子判定のみを実装し、詳細な検証はPhase 2以降で追加する。
"""

from pathlib import Path


def is_pdf_file(filename: str) -> bool:
    """ファイル名の拡張子がPDFかどうかを判定する。

    大文字・小文字は区別しない。パス付きのファイル名も受け付ける。

    Args:
        filename: 判定対象のファイル名またはパス。

    Returns:
        拡張子が ``.pdf`` の場合は True、それ以外は False。
    """
    return Path(filename).suffix.lower() == ".pdf"
