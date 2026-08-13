"""請求書基本情報の抽出モジュール。

PDF本文テキストから取引先・日付・金額などの基本項目を抽出する。
品目などの明細抽出は行わない。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_PREFECTURE_PATTERN = re.compile(
    r"(北海道|東京都|京都府|大阪府|"
    r"青森県|岩手県|宮城県|秋田県|山形県|福島県|"
    r"茨城県|栃木県|群馬県|埼玉県|千葉県|神奈川県|"
    r"新潟県|富山県|石川県|福井県|山梨県|長野県|"
    r"岐阜県|静岡県|愛知県|三重県|"
    r"滋賀県|兵庫県|奈良県|和歌山県|"
    r"鳥取県|島根県|岡山県|広島県|山口県|"
    r"徳島県|香川県|愛媛県|高知県|"
    r"福岡県|佐賀県|長崎県|熊本県|大分県|宮崎県|鹿児島県|沖縄県)"
)

_HONORIFICS = ("御中", "様")
_DATE_PATTERNS = (
    re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"),
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
)
_SKIP_NAME_KEYWORDS = (
    "請求書",
    "請求書番号",
    "請求番号",
    "請求日",
    "支払",
    "税抜",
    "消費税",
    "品目",
    "数量",
    "単価",
    "金額",
    "invoice",
)


@dataclass(frozen=True)
class InvoiceBasicInfo:
    """請求書から抽出した基本情報。"""

    filename: str
    customer_name: str | None
    customer_address: str | None
    invoice_number: str | None
    invoice_date: str | None
    due_date: str | None
    subtotal: int | None
    tax: int | None
    total: int | None


def parse_amount(value: str) -> int | None:
    """金額文字列を整数へ変換する。

    ``¥`` / ``￥`` / ``,`` / ``円`` / 空白を除去する。
    変換できない場合は None を返す。

    Args:
        value: 金額を表す文字列。

    Returns:
        整数金額。変換できない場合は None。
    """
    cleaned = (
        value.replace("¥", "")
        .replace("￥", "")
        .replace("\xa5", "")
        .replace(",", "")
        .replace("，", "")
        .replace("円", "")
        .replace(" ", "")
        .replace("\u3000", "")
        .strip()
    )
    if not cleaned or not re.fullmatch(r"-?\d+", cleaned):
        return None
    return int(cleaned)


def parse_date(value: str) -> str | None:
    """日付文字列を ``YYYY-MM-DD`` へ変換する。

    ``YYYY/MM/DD``、``YYYY-MM-DD``、``YYYY年M月D日`` を扱う。
    不正な日付は None を返す。

    Args:
        value: 日付を表す文字列。

    Returns:
        ``YYYY-MM-DD``。変換できない場合は None。
    """
    text = value.strip()
    if not text:
        return None

    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        try:
            parsed = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
        return parsed.isoformat()
    return None


def parse_invoice_basic_info(filename: str, text: str) -> InvoiceBasicInfo:
    """本文テキストから請求書基本情報を抽出する。

    取得できない項目は None とし、他項目の抽出は継続する。
    同一項目が複数回出現する場合は、値が同じなら1件として扱い、
    金額がページごとに異なる場合は合計する。

    Args:
        filename: 元PDFファイル名。
        text: PDF本文テキスト。

    Returns:
        抽出した請求書基本情報。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return InvoiceBasicInfo(
        filename=filename,
        customer_name=_extract_customer_name(lines),
        customer_address=_extract_customer_address(lines),
        invoice_number=_first_labeled_text(
            lines,
            ("請求書番号", "請求番号", "Invoice No.", "Invoice No"),
        ),
        invoice_date=parse_date(_first_labeled_text(lines, ("請求日",)) or ""),
        due_date=parse_date(
            _first_labeled_text(lines, ("お支払期限", "支払期限", "支払期日")) or ""
        ),
        subtotal=_resolve_amounts(_all_labeled_amounts(lines, ("税抜金額", "税抜合計", "小計"))),
        tax=_resolve_amounts(_all_labeled_amounts(lines, ("消費税額", "消費税"))),
        total=_extract_total(lines),
    )


def _extract_total(lines: list[str]) -> int | None:
    for labels in (
        ("ご請求金額（税込）", "ご請求金額(税込)"),
        ("ご請求金額",),
        ("合計金額",),
        ("請求金額",),
    ):
        amounts = _all_labeled_amounts(lines, labels)
        resolved = _resolve_amounts(amounts)
        if resolved is not None:
            return resolved
    return None


def _extract_customer_name(lines: list[str]) -> str | None:
    for line in lines:
        if _looks_like_label_line(line):
            continue
        for honorific in _HONORIFICS:
            if line.endswith(honorific):
                name = line[: -len(honorific)].strip()
                return name or None

    for line in lines:
        if "株式会社" not in line:
            continue
        if _looks_like_label_line(line):
            continue
        return line
    return None


def _extract_customer_address(lines: list[str]) -> str | None:
    for line in lines:
        if _looks_like_label_line(line):
            continue
        if any(line.endswith(honorific) for honorific in _HONORIFICS):
            continue
        if _PREFECTURE_PATTERN.search(line):
            return line
    return None


def _looks_like_label_line(line: str) -> bool:
    lowered = line.lower()
    return any(keyword.lower() in lowered for keyword in _SKIP_NAME_KEYWORDS)


def _first_labeled_text(lines: list[str], labels: tuple[str, ...]) -> str | None:
    values = _iter_labeled_values(lines, labels)
    if not values:
        return None
    return values[0]


def _all_labeled_amounts(lines: list[str], labels: tuple[str, ...]) -> list[int]:
    amounts: list[int] = []
    for value in _iter_labeled_values(lines, labels):
        amount = parse_amount(value)
        if amount is not None:
            amounts.append(amount)
    return amounts


def _iter_labeled_values(lines: list[str], labels: tuple[str, ...]) -> list[str]:
    ordered_labels = tuple(sorted(labels, key=len, reverse=True))
    values: list[str] = []
    for index, line in enumerate(lines):
        matched_label = _match_label(line, ordered_labels)
        if matched_label is None:
            continue
        rest = line[len(matched_label) :].strip()
        rest = re.sub(r"^[（(]税込[)）]\s*", "", rest).strip()
        rest = rest.lstrip(":：").strip()
        if rest:
            values.append(rest)
            continue
        if index + 1 < len(lines):
            values.append(lines[index + 1])
    return values


def _match_label(line: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        if line.startswith(label):
            return label
    return None


def _resolve_amounts(amounts: list[int]) -> int | None:
    if not amounts:
        return None
    if len(set(amounts)) == 1:
        return amounts[0]
    return sum(amounts)
