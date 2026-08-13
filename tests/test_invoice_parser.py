"""pdf_flow.invoice_parser のテスト。"""

from pdf_flow.invoice_parser import parse_amount, parse_date, parse_invoice_basic_info

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
USBメモリ 32GB
5
¥1,200
¥6,000
税抜金額
¥11,400
消費税
¥1,140
請求金額
¥12,540
2 / 2
"""


def test_parse_invoice_number_halfwidth_colon() -> None:
    """半角コロン付きの請求書番号を抽出できること。"""
    info = parse_invoice_basic_info("a.pdf", "請求書番号: INV-202608-001")
    assert info.invoice_number == "INV-202608-001"


def test_parse_invoice_number_fullwidth_colon() -> None:
    """全角コロン付きの請求書番号を抽出できること。"""
    info = parse_invoice_basic_info("a.pdf", "請求書番号：INV-202608-001")
    assert info.invoice_number == "INV-202608-001"


def test_parse_invoice_number_strips_spaces() -> None:
    """請求書番号の前後空白を除去できること。"""
    info = parse_invoice_basic_info("a.pdf", "請求書番号:  INV-202608-001  ")
    assert info.invoice_number == "INV-202608-001"


def test_parse_date_slash() -> None:
    """スラッシュ区切り日付を YYYY-MM-DD に変換できること。"""
    assert parse_date("2026/08/14") == "2026-08-14"


def test_parse_date_hyphen() -> None:
    """ハイフン区切り日付を YYYY-MM-DD に変換できること。"""
    assert parse_date("2026-08-14") == "2026-08-14"


def test_parse_date_japanese() -> None:
    """日本語日付を YYYY-MM-DD に変換できること。"""
    assert parse_date("2026年8月14日") == "2026-08-14"


def test_parse_date_invalid_returns_none() -> None:
    """不正な日付は None になること。"""
    assert parse_date("2026/13/40") is None
    assert parse_date("日付なし") is None


def test_parse_amount_variants() -> None:
    """金額表記のゆれを整数へ変換できること。"""
    assert parse_amount("¥15,000") == 15000
    assert parse_amount("￥15,000") == 15000
    assert parse_amount("15,000円") == 15000
    assert parse_amount("15000") == 15000


def test_parse_amount_invalid_returns_none() -> None:
    """不正な金額は None になること。"""
    assert parse_amount("") is None
    assert parse_amount("ABC") is None
    assert parse_amount("¥") is None


def test_parse_customer_name_strips_honorific() -> None:
    """御中を除去して取引先名を抽出できること。"""
    info = parse_invoice_basic_info("a.pdf", "株式会社サンプル販売 御中")
    assert info.customer_name == "株式会社サンプル販売"

    info = parse_invoice_basic_info("a.pdf", "テスト工業株式会社 御中")
    assert info.customer_name == "テスト工業株式会社"


def test_parse_customer_address() -> None:
    """都道府県を含む日本語住所を抽出できること。"""
    text = "株式会社サンプル販売 御中\n福岡県福岡市博多区博多駅前1-2-3"
    info = parse_invoice_basic_info("a.pdf", text)
    assert info.customer_address == "福岡県福岡市博多区博多駅前1-2-3"


def test_parse_partial_missing_due_date() -> None:
    """支払期限がなくても他項目を取得できること。"""
    text = """
請求書番号: INV-1
請求日: 2026/08/14
株式会社サンプル販売 御中
税抜金額: ¥10,000
"""
    info = parse_invoice_basic_info("a.pdf", text)
    assert info.invoice_number == "INV-1"
    assert info.invoice_date == "2026-08-14"
    assert info.customer_name == "株式会社サンプル販売"
    assert info.subtotal == 10000
    assert info.due_date is None


def test_parse_duplicate_basic_fields_on_multiple_pages() -> None:
    """同じ基本情報が複数回出現しても結果が壊れないこと。"""
    text = SAMPLE_001_TEXT + "\n" + SAMPLE_001_TEXT
    info = parse_invoice_basic_info("dup.pdf", text)
    assert info.invoice_number == "INV-202608-001"
    assert info.invoice_date == "2026-08-14"
    assert info.due_date == "2026-09-30"
    assert info.customer_name == "株式会社サンプル販売"
    assert info.customer_address == "福岡県福岡市博多区博多駅前1-2-3"
    assert info.subtotal == 15000
    assert info.tax == 1500
    assert info.total == 16500


def test_parse_sample_invoice_001_text() -> None:
    """sample_invoice_001 相当のテキストから基本情報を抽出できること。"""
    info = parse_invoice_basic_info("sample_invoice_001.pdf", SAMPLE_001_TEXT)
    assert info.invoice_number == "INV-202608-001"
    assert info.invoice_date == "2026-08-14"
    assert info.due_date == "2026-09-30"
    assert info.customer_name == "株式会社サンプル販売"
    assert info.customer_address == "福岡県福岡市博多区博多駅前1-2-3"
    assert info.subtotal == 15000
    assert info.tax == 1500
    assert info.total == 16500


def test_parse_sample_invoice_002_text() -> None:
    """sample_invoice_002 相当の複数ページテキストから基本情報を抽出できること。"""
    info = parse_invoice_basic_info("sample_invoice_002_2pages.pdf", SAMPLE_002_TEXT)
    assert info.invoice_number == "INV-202608-002"
    assert info.invoice_date == "2026-08-14"
    assert info.due_date == "2026-09-25"
    assert info.customer_name == "テスト工業株式会社"
    assert info.customer_address == "大阪府大阪市北区梅田2-3-4"
    assert info.subtotal == 25900
    assert info.tax == 2590
    assert info.total == 28490
