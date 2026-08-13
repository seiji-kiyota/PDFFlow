"""PDFFlow Ver1.0 Streamlit アプリケーション。"""

import streamlit as st

st.set_page_config(
    page_title="PDFFlow",
    page_icon="📄",
    layout="wide",
)

st.title("PDFFlow")
st.subheader("請求書PDFから請求情報・明細を抽出し、一覧化する業務支援ツール")
st.caption("Ver1.0")

st.divider()

st.markdown("### 処理フロー")

step1, step2, step3, step4, step5 = st.tabs(
    [
        "1. PDF取込",
        "2. PDF解析",
        "3. 抽出結果確認",
        "4. 請求一覧作成",
        "5. Excel / CSV出力",
    ]
)

with step1:
    st.info("この機能は今後のPhaseで実装予定です。")

with step2:
    st.info("この機能は今後のPhaseで実装予定です。")

with step3:
    st.info("この機能は今後のPhaseで実装予定です。")

with step4:
    st.info("この機能は今後のPhaseで実装予定です。")

with step5:
    st.info("この機能は今後のPhaseで実装予定です。")
