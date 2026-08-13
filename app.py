"""PDFFlow Ver1.0 Streamlit アプリケーション。"""

import streamlit as st

from pdf_flow.pdf_loader import PdfFileInfo, load_pdf_info
from pdf_flow.validators import validate_pdf

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


def format_file_size(size_bytes: int) -> str:
    """ファイルサイズを読みやすい単位で返す。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    kb = size_bytes / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    return f"{mb:.1f} MB"


if "loaded_pdfs" not in st.session_state:
    st.session_state.loaded_pdfs = []
if "pdf_errors" not in st.session_state:
    st.session_state.pdf_errors = []

with step1:
    uploaded_files = st.file_uploader(
        "請求書PDFを選択",
        type=["pdf"],
        accept_multiple_files=True,
        help="複数のPDFを同時に選択できます。",
    )

    if uploaded_files:
        loaded_pdfs: list[PdfFileInfo] = []
        pdf_errors: list[dict[str, str]] = []

        for uploaded in uploaded_files:
            data = uploaded.getvalue()
            result = validate_pdf(uploaded.name, data)
            if not result.ok:
                pdf_errors.append(
                    {
                        "filename": uploaded.name,
                        "error": result.error or "不正なPDFです。",
                    }
                )
                continue
            loaded_pdfs.append(load_pdf_info(uploaded.name, data))

        st.session_state.loaded_pdfs = loaded_pdfs
        st.session_state.pdf_errors = pdf_errors
    else:
        st.session_state.loaded_pdfs = []
        st.session_state.pdf_errors = []
        st.caption("PDFファイルを選択してください。複数ファイルを同時に選択できます。")

    loaded_pdfs = st.session_state.loaded_pdfs
    pdf_errors = st.session_state.pdf_errors

    if uploaded_files:
        st.write(f"読込PDF: {len(loaded_pdfs)}件")

        if loaded_pdfs:
            rows = [
                {
                    "ファイル名": info.filename,
                    "サイズ": format_file_size(info.size_bytes),
                    "ページ数": info.page_count,
                }
                for info in loaded_pdfs
            ]
            st.dataframe(rows, hide_index=True, width="stretch")

        for item in pdf_errors:
            st.error(f"{item['filename']}: {item['error']}")

with step2:
    st.info("この機能は今後のPhaseで実装予定です。")

with step3:
    st.info("この機能は今後のPhaseで実装予定です。")

with step4:
    st.info("この機能は今後のPhaseで実装予定です。")

with step5:
    st.info("この機能は今後のPhaseで実装予定です。")
