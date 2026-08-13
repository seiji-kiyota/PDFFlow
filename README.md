# PDFFlow

請求書PDFから請求情報・明細を抽出し、一覧化する業務支援ツールです。

## Ver1.0 の目的

取引先から受領した請求書PDFを読み込み、請求情報および明細情報を抽出して、日々の請求金額一覧を自動作成します。手入力作業の削減と転記ミス防止を目的とします。

## 現在の開発状況

現在は **Phase 2（PDF読込）** です。

請求書PDFを1件または複数件アップロードし、ファイル名、サイズ、ページ数を一覧表示できます。対応形式はPDFのみです。

PDF本文の解析や請求書項目の抽出は、まだ未実装です。以降のPhaseで実装します。

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

ブラウザで初期画面が開きます。Step 1「PDF取込」からPDFをアップロードできます。

## テストの実行

```bash
python -m pytest -q
```
