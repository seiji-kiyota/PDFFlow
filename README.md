# PDFFlow

請求書PDFから請求情報・明細を抽出し、一覧化する業務支援ツールです。

## Ver1.0 の目的

取引先から受領した請求書PDFを読み込み、請求情報および明細情報を抽出して、日々の請求金額一覧を自動作成します。手入力作業の削減と転記ミス防止を目的とします。

## 現在の開発状況

現在は **Phase 6（確認・修正UI）** です。

- Phase 2: 請求書PDFのアップロード。ファイル名、サイズ、ページ数を一覧表示できます。
- Phase 3: PDF本文テキストをページ単位で抽出できます。
- Phase 4: 取引先名、住所、請求書番号、請求日、支払期限、税抜金額、消費税、請求金額を抽出できます。
- Phase 5: 品目、数量、単価、明細金額を抽出できます。
- Phase 6: 基本情報と明細を画面上で修正し、明細の追加・削除、請求書の確定ができます。

対応形式は文字情報を持つPDFです。OCR（スキャン画像PDF）は未対応です。

Step 4の請求一覧作成、Step 5の Excel / CSV 出力は、まだ未実装です。

## セットアップ

Python 3.10 以降を推奨します。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux では、仮想環境の有効化を次のように行います。

```bash
source .venv/bin/activate
```

## Streamlit の起動

```bash
streamlit run app.py
```

ブラウザで初期画面が開きます。

1. Step 1「PDF取込」でPDFをアップロードします。
2. Step 2「PDF解析」で「PDFを解析」を押し、本文テキストを確認します。
3. Step 3「抽出結果確認」で基本情報・明細を確認し、必要なら修正して確定します。

## テストの実行

```bash
python -m pytest -q
```
