"""pdf_flow.invoice_detail_parser のテスト。"""

from pdf_flow.invoice_detail_parser import (
    InvoiceLineItem,
    line_item_matches_quantity_times_price,
    parse_invoice_details,
    parse_quantity,
)
from pdf_flow.invoice_parser import parse_invoice_basic_info

SAMPLE_001_TEXT = """
請 求 書
請求書番号: INV-202608-001
請求日: 2026/08/14
支払期限: 2026/09/30
株式会社サンプル販売 御中
福岡県福岡市博多区博多駅前1-2-3
株式会社 PDFFlow商事
東京都千代田区丸の内1-1-1
ご請求金額（税込）: ¥16,500
品目
数量
単価
金額
コピー用紙 A4
10
¥500
¥5,000
プリンタートナー
1
¥10,000
¥10,000
税抜金額
¥15,000
消費税
¥1,500
請求金額
¥16,500
1 / 1
"""

SAMPLE_002_TEXT = """
請 求 書
請求書番号: INV-202608-002
請求日: 2026/08/14
支払期限: 2026/09/25
テスト工業株式会社 御中
大阪府大阪市北区梅田2-3-4
株式会社 PDFFlow商事
東京都千代田区丸の内1-1-1
ご請求金額（税込）: ¥28,490
品目
数量
単価
金額
業務用ファイル
20
¥300
¥6,000
ボールペン 黒
50
¥120
¥6,000
付箋セット
10
¥250
¥2,500
税抜金額
¥14,500
消費税
¥1,450
請求金額
¥15,950
1 / 2
請 求 書
請求書番号: INV-202608-002
請求日: 2026/08/14
支払期限: 2026/09/25
テスト工業株式会社 御中
大阪府大阪市北区梅田2-3-4
株式会社 PDFFlow商事
東京都千代田区丸の内1-1-1
ご請求金額（税込）: ¥28,490
品目
数量
単価
金額
USBメモリ 32GB
5
¥1,200
¥6,000
HDMIケーブル
3
¥1,800
¥5,400
税抜金額
¥11,400
消費税
¥1,140
請求金額
¥12,540
2 / 2
"""

ROW_TABLE_TEXT = """
品目 数量 単価 金額
コピー用紙 A4 10 500 5,000
プリンタートナー 1 10,000 10,000
税抜金額 15,000
"""


def test_parse_single_line_item() -> None:
    """1件の明細を正しく取得できること。"""
    text = """
品目
数量
単価
金額
業務用ファイル
20
¥300
¥6,000
税抜金額
¥6,000
"""
    details = parse_invoice_details("a.pdf", text)
    assert details.item_count() == 1
    item = details.items[0]
    assert item.item_name == "業務用ファイル"
    assert item.quantity == 20
    assert item.unit_price == 300
    assert item.amount == 6000


def test_parse_multiple_line_items_preserves_order() -> None:
    """2件以上の明細を順番どおり取得できること。"""
    details = parse_invoice_details("a.pdf", SAMPLE_001_TEXT)
    assert details.item_count() == 2
    assert [item.item_name for item in details.items] == [
        "コピー用紙 A4",
        "プリンタートナー",
    ]


def test_parse_sample_invoice_001_details() -> None:
    """sample_invoice_001 相当の明細を抽出できること。"""
    details = parse_invoice_details("sample_invoice_001.pdf", SAMPLE_001_TEXT)
    assert details.items == (
        InvoiceLineItem("コピー用紙 A4", 10, 500, 5000),
        InvoiceLineItem("プリンタートナー", 1, 10000, 10000),
    )
    assert details.amount_total() == 15000
    basic = parse_invoice_basic_info("sample_invoice_001.pdf", SAMPLE_001_TEXT)
    assert basic.subtotal == details.amount_total()


def test_parse_sample_invoice_002_details_across_pages() -> None:
    """複数ページの明細を1つの一覧として順序どおり取得できること。"""
    details = parse_invoice_details("sample_invoice_002_2pages.pdf", SAMPLE_002_TEXT)
    assert [
        (item.item_name, item.quantity, item.unit_price, item.amount)
        for item in details.items
    ] == [
        ("業務用ファイル", 20, 300, 6000),
        ("ボールペン 黒", 50, 120, 6000),
        ("付箋セット", 10, 250, 2500),
        ("USBメモリ 32GB", 5, 1200, 6000),
        ("HDMIケーブル", 3, 1800, 5400),
    ]
    assert details.amount_total() == 25900
    basic = parse_invoice_basic_info("sample_invoice_002_2pages.pdf", SAMPLE_002_TEXT)
    assert basic.subtotal == details.amount_total()


def test_parse_row_style_table() -> None:
    """1行に品目・数量・単価・金額が並ぶ表を解析できること。"""
    details = parse_invoice_details("row.pdf", ROW_TABLE_TEXT)
    assert details.item_count() == 2
    assert details.items[0] == InvoiceLineItem("コピー用紙 A4", 10, 500, 5000)
    assert details.items[1] == InvoiceLineItem("プリンタートナー", 1, 10000, 10000)


def test_parse_amount_notations_in_line_items() -> None:
    """明細金額の表記ゆれを整数へ変換できること。"""
    text = """
品目 数量 単価 金額
品目A 1 500 500
品目B 1 10,000 10,000
品目C 1 ¥10,000 ¥10,000
品目D 1 10,000円 10,000円
税抜金額
"""
    details = parse_invoice_details("a.pdf", text)
    assert [item.unit_price for item in details.items] == [500, 10000, 10000, 10000]
    assert [item.amount for item in details.items] == [500, 10000, 10000, 10000]


def test_parse_quantity_integer_and_float() -> None:
    """整数・小数の数量を変換できること。"""
    assert parse_quantity("10") == 10
    assert parse_quantity("1.5") == 1.5


def test_parse_quantity_invalid_returns_none() -> None:
    """不正な数量は None になること。"""
    assert parse_quantity("") is None
    assert parse_quantity("ABC") is None
    assert parse_quantity("¥500") is None


def test_summary_rows_are_not_line_items() -> None:
    """小計・税抜・消費税・請求金額・合計を明細として扱わないこと。"""
    text = """
品目
数量
単価
金額
小計
10
100
1000
税抜金額
¥15,000
消費税
¥1,500
請求金額
¥16,500
合計
¥16,500
"""
    details = parse_invoice_details("a.pdf", text)
    assert details.items == ()


def test_partial_line_item_keeps_known_fields() -> None:
    """数量がなくても品目と金額を保持できること。"""
    text = """
品目
数量
単価
金額
作業費
¥30,000
税抜金額
¥30,000
"""
    details = parse_invoice_details("a.pdf", text)
    assert details.item_count() == 1
    item = details.items[0]
    assert item.item_name == "作業費"
    assert item.quantity is None
    assert item.unit_price is None
    assert item.amount == 30000


def test_no_line_items_returns_empty_list() -> None:
    """明細がないテキストでも空一覧として安全に処理できること。"""
    details = parse_invoice_details("empty.pdf", "請求書番号: INV-1\n請求日: 2026/08/14")
    assert details.items == ()
    assert details.item_count() == 0
    assert details.amount_total() == 0


def test_line_item_consistency_helper_does_not_rewrite() -> None:
    """数量×単価と明細金額の一致確認は値を変更しないこと。"""
    matching = InvoiceLineItem("コピー用紙 A4", 10, 500, 5000)
    mismatched = InvoiceLineItem("作業費", 1, 100, 999)
    incomplete = InvoiceLineItem("作業費", None, None, 30000)
    assert line_item_matches_quantity_times_price(matching) is True
    assert line_item_matches_quantity_times_price(mismatched) is False
    assert line_item_matches_quantity_times_price(incomplete) is None
    assert mismatched.amount == 999
