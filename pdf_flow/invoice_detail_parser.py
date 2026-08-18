"""請求明細の抽出モジュール。

PDF本文テキストから品目・数量・単価・明細金額を抽出する。
請求書基本情報の抽出は行わない。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pdf_flow.invoice_parser import parse_amount

_HEADER_LABELS = {"品目", "数量", "単価", "金額"}
_SUMMARY_PREFIXES = (
    "税抜金額",
    "税抜合計",
    "小計",
    "消費税額",
    "消費税",
    "ご請求金額",
    "請求金額",
    "合計金額",
    "合計",
    "備考",
)
_PAGE_NUMBER_PATTERN = re.compile(r"^\d+\s*/\s*\d+$")


@dataclass(frozen=True)
class InvoiceLineItem:
    """請求明細の1行。"""

    item_name: str
    quantity: float | int | None
    unit_price: int | None
    amount: int | None


@dataclass(frozen=True)
class InvoiceDetails:
    """1請求書分の明細一覧。"""

    filename: str
    items: tuple[InvoiceLineItem, ...]

    def item_count(self) -> int:
        """明細件数を返す。"""
        return len(self.items)

    def amount_total(self) -> int:
        """明細金額の合計を返す。未取得の金額は加算しない。"""
        return sum(item.amount for item in self.items if item.amount is not None)


def parse_quantity(value: str) -> float | int | None:
    """数量文字列を数値へ変換する。

    整数はそのまま ``int``、小数は ``float`` として返す。
    変換できない場合は None を返す。

    Args:
        value: 数量を表す文字列。

    Returns:
        数量。変換できない場合は None。
    """
    cleaned = (
        value.replace(",", "")
        .replace("，", "")
        .replace(" ", "")
        .replace("\u3000", "")
        .strip()
    )
    if not cleaned:
        return None
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        number = float(cleaned)
        if number.is_integer():
            return int(number)
        return number
    return None


def line_item_matches_quantity_times_price(item: InvoiceLineItem) -> bool | None:
    """数量 × 単価 が明細金額と一致するかを返す。

    いずれかが未取得の場合は None。結果に応じて明細値は変更しない。
    """
    if item.quantity is None or item.unit_price is None or item.amount is None:
        return None
    return item.quantity * item.unit_price == item.amount


def parse_invoice_details(filename: str, text: str) -> InvoiceDetails:
    """本文テキストから請求明細を抽出する。

    明細表ヘッダー以降を読み、小計・税・合計行は除外する。
    複数ページにまたがる明細は出現順の1つの一覧として返す。
    明細が無い場合は空の一覧を返す。

    Args:
        filename: 元PDFファイル名。
        text: PDF本文テキスト。

    Returns:
        抽出した請求明細。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items: list[InvoiceLineItem] = []
    index = 0
    while index < len(lines):
        if _is_table_header(lines[index]):
            index = _skip_header_lines(lines, index)
            block_items, index = _parse_item_block(lines, index)
            items.extend(block_items)
            continue
        index += 1
    return InvoiceDetails(filename=filename, items=tuple(items))


def _is_table_header(line: str) -> bool:
    if line in _HEADER_LABELS:
        return line == "品目"
    return "品目" in line and "数量" in line and "単価" in line


def _skip_header_lines(lines: list[str], index: int) -> int:
    index += 1
    while index < len(lines) and lines[index] in _HEADER_LABELS:
        index += 1
    return index


def _parse_item_block(
    lines: list[str], index: int
) -> tuple[list[InvoiceLineItem], int]:
    items: list[InvoiceLineItem] = []
    while index < len(lines):
        line = lines[index]
        if _is_summary_line(line):
            break
        if _is_table_header(line) or line in _HEADER_LABELS:
            break
        if _is_noise_line(line):
            index += 1
            continue
        row_item = _parse_single_line_item(line)
        if row_item is not None:
            items.append(row_item)
            index += 1
            continue
        item, index = _parse_stacked_item(lines, index)
        if item is not None:
            items.append(item)
    return items, index


def _parse_single_line_item(line: str) -> InvoiceLineItem | None:
    parts = line.split()
    if len(parts) < 4:
        return None
    quantity = parse_quantity(parts[-3])
    unit_price = parse_amount(parts[-2])
    amount = parse_amount(parts[-1])
    item_name = " ".join(parts[:-3]).strip()
    if not item_name or _is_summary_line(item_name) or item_name in _HEADER_LABELS:
        return None
    if quantity is None and unit_price is None and amount is None:
        return None
    if quantity is None or (unit_price is None and amount is None):
        return None
    return InvoiceLineItem(
        item_name=item_name,
        quantity=quantity,
        unit_price=unit_price,
        amount=amount,
    )


def _parse_stacked_item(
    lines: list[str], index: int
) -> tuple[InvoiceLineItem | None, int]:
    name = lines[index]
    if _looks_numeric(name) or _is_summary_line(name) or name in _HEADER_LABELS:
        return None, index + 1

    numbers: list[str] = []
    cursor = index + 1
    while cursor < len(lines) and len(numbers) < 3:
        next_line = lines[cursor]
        if (
            _is_summary_line(next_line)
            or next_line in _HEADER_LABELS
            or _is_table_header(next_line)
        ):
            break
        if not _looks_numeric(next_line):
            break
        numbers.append(next_line)
        cursor += 1

    quantity: float | int | None = None
    unit_price: int | None = None
    amount: int | None = None
    if len(numbers) == 3:
        quantity = parse_quantity(numbers[0])
        unit_price = parse_amount(numbers[1])
        amount = parse_amount(numbers[2])
    elif len(numbers) == 2:
        quantity = parse_quantity(numbers[0])
        amount = parse_amount(numbers[1])
    elif len(numbers) == 1:
        amount = parse_amount(numbers[0])

    return (
        InvoiceLineItem(
            item_name=name,
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
        ),
        cursor,
    )


def _is_summary_line(line: str) -> bool:
    return any(line == prefix or line.startswith(prefix) for prefix in _SUMMARY_PREFIXES)


def _is_noise_line(line: str) -> bool:
    compact = line.replace(" ", "")
    return bool(_PAGE_NUMBER_PATTERN.fullmatch(line)) or compact == "請求書"


def _looks_numeric(line: str) -> bool:
    return parse_quantity(line) is not None or parse_amount(line) is not None
