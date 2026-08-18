"""請求書の確認・修正・確定ロジック。

自動解析結果は変更せず、編集用コピーと確定データを別管理する。
"""

from __future__ import annotations

from dataclasses import dataclass

from pdf_flow.invoice_detail_parser import InvoiceDetails, InvoiceLineItem, parse_quantity
from pdf_flow.invoice_parser import InvoiceBasicInfo, parse_amount, parse_date

STATUS_UNREVIEWED = "未確認"
STATUS_EDITING = "編集中"
STATUS_CONFIRMED = "確定済み"

_ITEM_NAME_KEY = "品目"
_QUANTITY_KEY = "数量"
_UNIT_PRICE_KEY = "単価"
_AMOUNT_KEY = "明細金額"


@dataclass(frozen=True)
class ValidationResult:
    """編集内容の検証結果。"""

    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ConfirmedInvoice:
    """ユーザーが確定した請求書データ。"""

    filename: str
    basic: InvoiceBasicInfo
    details: InvoiceDetails


def empty_line_item() -> dict[str, object]:
    """空の明細行を返す。"""
    return {
        _ITEM_NAME_KEY: "",
        _QUANTITY_KEY: None,
        _UNIT_PRICE_KEY: None,
        _AMOUNT_KEY: None,
    }


def create_editable_basic(info: InvoiceBasicInfo) -> dict[str, object]:
    """自動抽出の基本情報から編集用コピーを作成する。

    元の ``InvoiceBasicInfo`` は変更しない。
    """
    return {
        "filename": info.filename,
        "customer_name": info.customer_name or "",
        "customer_address": info.customer_address or "",
        "invoice_number": info.invoice_number or "",
        "invoice_date": info.invoice_date or "",
        "due_date": info.due_date or "",
        "subtotal": info.subtotal,
        "tax": info.tax,
        "total": info.total,
    }


def create_editable_details(details: InvoiceDetails) -> list[dict[str, object]]:
    """自動抽出の明細から編集用コピーを作成する。

    元の ``InvoiceDetails`` は変更しない。
    """
    return [
        {
            _ITEM_NAME_KEY: item.item_name,
            _QUANTITY_KEY: item.quantity,
            _UNIT_PRICE_KEY: item.unit_price,
            _AMOUNT_KEY: item.amount,
        }
        for item in details.items
    ]


def add_empty_line(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """明細行を1行追加した新しい一覧を返す。"""
    updated = [dict(row) for row in rows]
    updated.append(empty_line_item())
    return updated


def delete_line(rows: list[dict[str, object]], index: int) -> list[dict[str, object]]:
    """指定行を削除した新しい一覧を返す。"""
    updated = [dict(row) for row in rows]
    del updated[index]
    return updated


def reset_editable(
    info: InvoiceBasicInfo, details: InvoiceDetails
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """自動抽出値から編集用データを作り直す。"""
    return create_editable_basic(info), create_editable_details(details)


def sanitize_editor_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """data_editor 由来の行から NaN を除き、列をそろえる。"""
    sanitized: list[dict[str, object]] = []
    for row in rows:
        name = row.get(_ITEM_NAME_KEY)
        if name is None or _is_nan(name):
            name = ""
        sanitized.append(
            {
                _ITEM_NAME_KEY: str(name),
                _QUANTITY_KEY: None if _is_nan(row.get(_QUANTITY_KEY)) else row.get(_QUANTITY_KEY),
                _UNIT_PRICE_KEY: None if _is_nan(row.get(_UNIT_PRICE_KEY)) else row.get(_UNIT_PRICE_KEY),
                _AMOUNT_KEY: None if _is_nan(row.get(_AMOUNT_KEY)) else row.get(_AMOUNT_KEY),
            }
        )
    return sanitized


def named_line_items(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """品目が入力されている明細行だけを返す。"""
    items: list[dict[str, object]] = []
    for row in sanitize_editor_rows(rows):
        if str(row[_ITEM_NAME_KEY]).strip():
            items.append(row)
    return items


def detail_item_count(rows: list[dict[str, object]]) -> int:
    """品目ありの明細件数を返す。"""
    return len(named_line_items(rows))


def detail_amount_total(rows: list[dict[str, object]]) -> int:
    """品目あり明細の金額合計を返す。未取得は加算しない。"""
    total = 0
    for row in named_line_items(rows):
        amount, valid = _normalize_int(row.get(_AMOUNT_KEY))
        if valid and amount is not None:
            total += amount
    return total


def validate_invoice(
    basic: dict[str, object], rows: list[dict[str, object]]
) -> ValidationResult:
    """編集中の基本情報と明細を検証する。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not str(basic.get("customer_name") or "").strip():
        errors.append("取引先名が未入力です。")
    if not str(basic.get("invoice_number") or "").strip():
        errors.append("請求書番号が未入力です。")

    invoice_date = str(basic.get("invoice_date") or "").strip()
    if not invoice_date:
        errors.append("請求日が未入力です。")
    elif parse_date(invoice_date) is None:
        errors.append("請求日が不正です。")

    due_date = str(basic.get("due_date") or "").strip()
    if due_date and parse_date(due_date) is None:
        errors.append("支払期限が不正です。")

    _validate_amount_field(basic.get("total"), "請求金額（税込）", errors, required=True)
    _validate_amount_field(basic.get("subtotal"), "税抜金額", errors, required=False)
    _validate_amount_field(basic.get("tax"), "消費税", errors, required=False)

    for index, row in enumerate(sanitize_editor_rows(rows), start=1):
        name = str(row[_ITEM_NAME_KEY]).strip()
        has_values = _row_has_values(row)
        if not name:
            if has_values:
                warnings.append(f"明細{index}行目: 品目が空のため確定対象から除外します。")
            continue

        quantity, quantity_ok = _normalize_quantity(row.get(_QUANTITY_KEY))
        if not quantity_ok:
            errors.append(f"明細{index}行目: 数量が不正です。")
        elif quantity is not None and quantity < 0:
            errors.append(f"明細{index}行目: 数量が負数です。")

        unit_price, unit_ok = _normalize_int(row.get(_UNIT_PRICE_KEY))
        if not unit_ok:
            errors.append(f"明細{index}行目: 単価が不正です。")
        elif unit_price is not None and unit_price < 0:
            errors.append(f"明細{index}行目: 単価が負数です。")

        amount, amount_ok = _normalize_int(row.get(_AMOUNT_KEY))
        if not amount_ok:
            errors.append(f"明細{index}行目: 明細金額が不正です。")
        elif amount is not None and amount < 0:
            errors.append(f"明細{index}行目: 明細金額が負数です。")

        if (
            quantity is not None
            and unit_price is not None
            and amount is not None
            and quantity * unit_price != amount
        ):
            warnings.append(f"明細{index}行目: 数量×単価が明細金額と一致しません。")

    return ValidationResult(ok=not errors, errors=tuple(errors), warnings=tuple(warnings))


def confirm_invoice(
    basic: dict[str, object], rows: list[dict[str, object]]
) -> tuple[ConfirmedInvoice | None, ValidationResult]:
    """検証を通過した編集内容から確定データを生成する。"""
    result = validate_invoice(basic, rows)
    if not result.ok:
        return None, result

    filename = str(basic.get("filename") or "")
    confirmed = ConfirmedInvoice(
        filename=filename,
        basic=_to_basic_info(basic),
        details=_to_details(filename, rows),
    )
    return confirmed, result


def list_confirmed_invoices(
    confirmed: list[ConfirmedInvoice | None],
) -> list[ConfirmedInvoice]:
    """確定済み請求書だけを返す。"""
    return [item for item in confirmed if item is not None]


def resolve_status(
    edited_basic: dict[str, object],
    edited_rows: list[dict[str, object]],
    parsed_basic: InvoiceBasicInfo,
    parsed_details: InvoiceDetails,
    confirmed: ConfirmedInvoice | None,
) -> str:
    """編集内容から請求書の確認状態を返す。"""
    if confirmed is not None and _matches_confirmed(edited_basic, edited_rows, confirmed):
        return STATUS_CONFIRMED
    if _matches_parsed(edited_basic, edited_rows, parsed_basic, parsed_details):
        return STATUS_UNREVIEWED
    return STATUS_EDITING


def _validate_amount_field(
    value: object, label: str, errors: list[str], *, required: bool
) -> None:
    amount, valid = _normalize_int(value)
    if not valid:
        errors.append(f"{label}が不正です。")
        return
    if required and amount is None:
        errors.append(f"{label}が未入力です。")
        return
    if amount is not None and amount < 0:
        errors.append(f"{label}が負数です。")


def _to_basic_info(basic: dict[str, object]) -> InvoiceBasicInfo:
    invoice_date = parse_date(str(basic.get("invoice_date") or "").strip())
    due_raw = str(basic.get("due_date") or "").strip()
    due_date = parse_date(due_raw) if due_raw else None
    subtotal, _ = _normalize_int(basic.get("subtotal"))
    tax, _ = _normalize_int(basic.get("tax"))
    total, _ = _normalize_int(basic.get("total"))
    return InvoiceBasicInfo(
        filename=str(basic.get("filename") or ""),
        customer_name=_blank_to_none(str(basic.get("customer_name") or "")),
        customer_address=_blank_to_none(str(basic.get("customer_address") or "")),
        invoice_number=_blank_to_none(str(basic.get("invoice_number") or "")),
        invoice_date=invoice_date,
        due_date=due_date,
        subtotal=subtotal,
        tax=tax,
        total=total,
    )


def _to_details(filename: str, rows: list[dict[str, object]]) -> InvoiceDetails:
    items: list[InvoiceLineItem] = []
    for row in named_line_items(rows):
        quantity, _ = _normalize_quantity(row.get(_QUANTITY_KEY))
        unit_price, _ = _normalize_int(row.get(_UNIT_PRICE_KEY))
        amount, _ = _normalize_int(row.get(_AMOUNT_KEY))
        items.append(
            InvoiceLineItem(
                item_name=str(row[_ITEM_NAME_KEY]).strip(),
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
            )
        )
    return InvoiceDetails(filename=filename, items=tuple(items))


def _matches_parsed(
    edited_basic: dict[str, object],
    edited_rows: list[dict[str, object]],
    parsed_basic: InvoiceBasicInfo,
    parsed_details: InvoiceDetails,
) -> bool:
    return _comparable_basic(create_editable_basic(parsed_basic)) == _comparable_basic(
        edited_basic
    ) and _comparable_rows(create_editable_details(parsed_details)) == _comparable_rows(
        edited_rows
    )


def _matches_confirmed(
    edited_basic: dict[str, object],
    edited_rows: list[dict[str, object]],
    confirmed: ConfirmedInvoice,
) -> bool:
    return _comparable_basic(create_editable_basic(confirmed.basic)) == _comparable_basic(
        edited_basic
    ) and _comparable_rows(create_editable_details(confirmed.details)) == _comparable_rows(
        edited_rows
    )


def _comparable_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    comparable: list[dict[str, object]] = []
    for row in named_line_items(rows):
        quantity, _ = _normalize_quantity(row.get(_QUANTITY_KEY))
        unit_price, _ = _normalize_int(row.get(_UNIT_PRICE_KEY))
        amount, _ = _normalize_int(row.get(_AMOUNT_KEY))
        comparable.append(
            {
                _ITEM_NAME_KEY: str(row[_ITEM_NAME_KEY]).strip(),
                _QUANTITY_KEY: quantity,
                _UNIT_PRICE_KEY: unit_price,
                _AMOUNT_KEY: amount,
            }
        )
    return comparable


def _comparable_basic(basic: dict[str, object]) -> dict[str, object]:
    comparable = dict(basic)
    comparable["customer_name"] = str(basic.get("customer_name") or "")
    comparable["customer_address"] = str(basic.get("customer_address") or "")
    comparable["invoice_number"] = str(basic.get("invoice_number") or "")
    comparable["invoice_date"] = str(basic.get("invoice_date") or "")
    comparable["due_date"] = str(basic.get("due_date") or "")
    subtotal, _ = _normalize_int(basic.get("subtotal"))
    tax, _ = _normalize_int(basic.get("tax"))
    total, _ = _normalize_int(basic.get("total"))
    comparable["subtotal"] = subtotal
    comparable["tax"] = tax
    comparable["total"] = total
    return comparable


def _row_has_values(row: dict[str, object]) -> bool:
    return any(
        value not in (None, "")
        for value in (row.get(_QUANTITY_KEY), row.get(_UNIT_PRICE_KEY), row.get(_AMOUNT_KEY))
    )


def _blank_to_none(value: str) -> str | None:
    text = value.strip()
    return text or None


def _is_nan(value: object) -> bool:
    return isinstance(value, float) and value != value


def _normalize_int(value: object) -> tuple[int | None, bool]:
    if value is None or value == "":
        return None, True
    if _is_nan(value):
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return value, True
    if isinstance(value, float):
        if value.is_integer():
            return int(value), True
        return None, False
    if isinstance(value, str):
        parsed = parse_amount(value)
        return parsed, parsed is not None
    return None, False


def _normalize_quantity(value: object) -> tuple[float | int | None, bool]:
    if value is None or value == "":
        return None, True
    if _is_nan(value):
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        return value, True
    if isinstance(value, float):
        if value.is_integer():
            return int(value), True
        return value, True
    if isinstance(value, str):
        parsed = parse_quantity(value)
        return parsed, parsed is not None
    return None, False
