# PDFFlow

請求書PDFから請求情報・明細を抽出し、一覧化する業務支援ツールです。

## Ver1.0 の目的

取引先から受領した請求書PDFを読み込み、請求情報および明細情報を抽出して、日々の請求金額一覧を自動作成します。手入力作業の削減と転記ミス防止を目的とします。

## 現在の開発状況

現在は **Phase 1（プロジェクト基盤）** です。

Streamlitの初期画面とプロジェクト構成を整備しています。PDF解析・請求書情報抽出などの本機能は、以降のPhaseで実装します。

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

## テストの実行

```bash
python -m pytest -q
```
