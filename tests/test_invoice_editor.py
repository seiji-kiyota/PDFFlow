"""pdf_flow.invoice_editor のテスト。"""

from pdf_flow.invoice_detail_parser import InvoiceDetails, InvoiceLineItem
from pdf_flow.invoice_editor import (
    STATUS_CONFIRMED,
    STATUS_EDITING,
    STATUS_UNREVIEWED,
    add_empty_line,
    confirm_invoice,
    create_editable_basic,
    create_editable_details,
    delete_line,
    detail_amount_total,
    detail_item_count,
    empty_line_item,
    list_confirmed_invoices,
    reset_editable,
    resolve_status,
    validate_invoice,
)
from pdf_flow.invoice_parser import InvoiceBasicInfo

PARSED_BASIC = InvoiceBasicInfo(
    filename="invoice.pdf",
    customer_name="株式会社サンプル販売",
    customer_address="福岡県福岡市博多区博多駅前1-2-3",
    invoice_number="INV-202608-001",
    invoice_date="2026-08-14",
    due_date="2026-09-30",
    subtotal=15000,
    tax=1500,
    total=16500,
)

PARSED_DETAILS = InvoiceDetails(
    filename="invoice.pdf",
    items=(
        InvoiceLineItem("コピー用紙 A4", 10, 500, 5000),
        InvoiceLineItem("プリンタートナー", 1, 10000, 10000),
    ),
)


def test_create_editable_does_not_mutate_parsed() -> None:
    """編集用データ作成後も自動抽出結果が変わらないこと。"""
    basic = create_editable_basic(PARSED_BASIC)
    details = create_editable_details(PARSED_DETAILS)
    basic["customer_name"] = "変更後"
    details[0]["品目"] = "変更後"
    assert PARSED_BASIC.customer_name == "株式会社サンプル販売"
    assert PARSED_DETAILS.items[0].item_name == "コピー用紙 A4"


def test_edit_basic_info_keeps_changed_value() -> None:
    """基本情報の変更値を保持できること。"""
    basic = create_editable_basic(PARSED_BASIC)
    basic["customer_name"] = "テスト工業株式会社"
    assert basic["customer_name"] == "テスト工業株式会社"
    assert PARSED_BASIC.customer_name == "株式会社サンプル販売"


def test_edit_line_item_keeps_changed_value() -> None:
    """明細の変更値を保持できること。"""
    rows = create_editable_details(PARSED_DETAILS)
    rows[0]["数量"] = 8
    rows[0]["明細金額"] = 4000
    assert rows[0]["数量"] == 8
    assert rows[0]["明細金額"] == 4000
    assert PARSED_DETAILS.items[0].quantity == 10


def test_add_empty_line_appends_row() -> None:
    """明細行を追加できること。"""
    rows = create_editable_details(PARSED_DETAILS)
    updated = add_empty_line(rows)
    assert len(updated) == 3
    assert updated[-1] == empty_line_item()
    assert len(rows) == 2


def test_delete_line_updates_count_and_total() -> None:
    """明細削除後の件数・合計が正しいこと。"""
    rows = create_editable_details(PARSED_DETAILS)
    updated = delete_line(rows, 0)
    assert detail_item_count(updated) == 1
    assert detail_amount_total(updated) == 10000


def test_reset_editable_restores_parsed_values() -> None:
    """編集結果を自動抽出値へ戻せること。"""
    basic = create_editable_basic(PARSED_BASIC)
    rows = create_editable_details(PARSED_DETAILS)
    basic["customer_name"] = "変更後"
    rows = add_empty_line(rows)
    rows[0]["品目"] = "変更後"
    reset_basic, reset_rows = reset_editable(PARSED_BASIC, PARSED_DETAILS)
    assert reset_basic["customer_name"] == "株式会社サンプル販売"
    assert detail_item_count(reset_rows) == 2
    assert reset_rows[0]["品目"] == "コピー用紙 A4"


def test_validate_missing_required_fields() -> None:
    """必須項目が未入力の場合にバリデーションエラーになること。"""
    basic = create_editable_basic(PARSED_BASIC)
    basic["customer_name"] = ""
    basic["invoice_number"] = ""
    basic["invoice_date"] = ""
    basic["total"] = None
    result = validate_invoice(basic, create_editable_details(PARSED_DETAILS))
    assert result.ok is False
    assert any("取引先名" in message for message in result.errors)
    assert any("請求書番号" in message for message in result.errors)
    assert any("請求日" in message for message in result.errors)
    assert any("請求金額" in message for message in result.errors)


def test_validate_invalid_date_cannot_confirm() -> None:
    """不正日付は確定不可になること。"""
    basic = create_editable_basic(PARSED_BASIC)
    basic["invoice_date"] = "2026/13/40"
    confirmed, result = confirm_invoice(basic, create_editable_details(PARSED_DETAILS))
    assert confirmed is None
    assert result.ok is False
    assert any("請求日" in message for message in result.errors)


def test_validate_negative_amount_cannot_confirm() -> None:
    """負数金額は確定不可になること。"""
    basic = create_editable_basic(PARSED_BASIC)
    basic["total"] = -1
    rows = create_editable_details(PARSED_DETAILS)
    rows[0]["明細金額"] = -100
    confirmed, result = confirm_invoice(basic, rows)
    assert confirmed is None
    assert result.ok is False
    assert any("負数" in message for message in result.errors)


def test_detail_amount_total_after_edit() -> None:
    """編集後の明細金額から合計を再計算できること。"""
    rows = create_editable_details(PARSED_DETAILS)
    rows[0]["明細金額"] = 4000
    rows[1]["明細金額"] = 8000
    assert detail_amount_total(rows) == 12000


def test_confirm_invoice_contains_basic_and_details() -> None:
    """確定データに基本情報と明細が含まれること。"""
    basic = create_editable_basic(PARSED_BASIC)
    rows = add_empty_line(create_editable_details(PARSED_DETAILS))
    confirmed, result = confirm_invoice(basic, rows)
    assert result.ok is True
    assert confirmed is not None
    assert confirmed.filename == "invoice.pdf"
    assert confirmed.basic.customer_name == "株式会社サンプル販売"
    assert confirmed.basic.invoice_number == "INV-202608-001"
    assert confirmed.basic.invoice_date == "2026-08-14"
    assert confirmed.basic.total == 16500
    assert confirmed.details.item_count() == 2
    assert confirmed.details.items[0].item_name == "コピー用紙 A4"
    assert list_confirmed_invoices([None, confirmed]) == [confirmed]


def test_resolve_status_for_edit_and_confirm() -> None:
    """未確認・編集中・確定済みの状態遷移ができること。"""
    basic = create_editable_basic(PARSED_BASIC)
    rows = create_editable_details(PARSED_DETAILS)
    assert (
        resolve_status(basic, rows, PARSED_BASIC, PARSED_DETAILS, None)
        == STATUS_UNREVIEWED
    )

    basic["customer_name"] = "変更後"
    assert (
        resolve_status(basic, rows, PARSED_BASIC, PARSED_DETAILS, None)
        == STATUS_EDITING
    )

    confirmed, result = confirm_invoice(basic, rows)
    assert result.ok is True
    assert confirmed is not None
    assert (
        resolve_status(basic, rows, PARSED_BASIC, PARSED_DETAILS, confirmed)
        == STATUS_CONFIRMED
    )

    basic["customer_name"] = "再編集"
    assert (
        resolve_status(basic, rows, PARSED_BASIC, PARSED_DETAILS, confirmed)
        == STATUS_EDITING
    )
