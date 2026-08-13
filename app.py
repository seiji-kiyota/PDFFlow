"""PDFFlow Ver1.0 Streamlit アプリケーション。"""

import streamlit as st

from pdf_flow.pdf_loader import PdfFileInfo, load_pdf_info
from pdf_flow.text_extractor import PdfTextExtraction, extract_pdf_text
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
if "loaded_pdf_bytes" not in st.session_state:
    st.session_state.loaded_pdf_bytes = []
if "pdf_errors" not in st.session_state:
    st.session_state.pdf_errors = []
if "extracted_texts" not in st.session_state:
    st.session_state.extracted_texts = []
if "extraction_errors" not in st.session_state:
    st.session_state.extraction_errors = []
if "loaded_pdf_identity" not in st.session_state:
    st.session_state.loaded_pdf_identity = ()

with step1:
    uploaded_files = st.file_uploader(
        "請求書PDFを選択",
        type=["pdf"],
        accept_multiple_files=True,
        help="複数のPDFを同時に選択できます。",
    )

    if uploaded_files:
        loaded_pdfs: list[PdfFileInfo] = []
        loaded_pdf_bytes: list[bytes] = []
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
            loaded_pdf_bytes.append(data)

        st.session_state.loaded_pdfs = loaded_pdfs
        st.session_state.loaded_pdf_bytes = loaded_pdf_bytes
        st.session_state.pdf_errors = pdf_errors
    else:
        st.session_state.loaded_pdfs = []
        st.session_state.loaded_pdf_bytes = []
        st.session_state.pdf_errors = []
        st.caption("PDFファイルを選択してください。複数ファイルを同時に選択できます。")

    loaded_identity = tuple(
        (info.filename, info.size_bytes, info.page_count)
        for info in st.session_state.loaded_pdfs
    )
    if st.session_state.loaded_pdf_identity != loaded_identity:
        st.session_state.loaded_pdf_identity = loaded_identity
        st.session_state.extracted_texts = []
        st.session_state.extraction_errors = []

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
    loaded_pdfs = st.session_state.loaded_pdfs
    loaded_pdf_bytes = st.session_state.loaded_pdf_bytes

    if not loaded_pdfs:
        st.info("先に Step 1 でPDFを取り込んでください。")
    else:
        st.write(f"対象PDF: {len(loaded_pdfs)}件")
        st.caption("取り込んだPDFから本文テキストをページ単位で抽出します。")

        if st.button("PDFを解析"):
            extracted_texts: list[PdfTextExtraction] = []
            extraction_errors: list[dict[str, str]] = []
            for info, data in zip(loaded_pdfs, loaded_pdf_bytes, strict=True):
                try:
                    extracted_texts.append(extract_pdf_text(info.filename, data))
                except Exception:
                    extraction_errors.append(
                        {
                            "filename": info.filename,
                            "error": "PDFのテキストを抽出できませんでした。",
                        }
                    )
            st.session_state.extracted_texts = extracted_texts
            st.session_state.extraction_errors = extraction_errors

        extracted_texts = st.session_state.extracted_texts
        extraction_errors = st.session_state.extraction_errors

        if not extracted_texts and not extraction_errors:
            st.caption("「PDFを解析」を押すと、抽出テキストを確認できます。")

        for item in extraction_errors:
            st.error(f"{item['filename']}: {item['error']}")

        for file_index, extraction in enumerate(extracted_texts):
            title = f"{extraction.filename}（{extraction.page_count}ページ）"
            with st.expander(title):
                if not extraction.has_text():
                    st.warning("文字情報を取得できませんでした。")
                for page in extraction.pages:
                    if page.text.strip():
                        st.text_area(
                            f"ページ {page.page_number}",
                            value=page.text,
                            height=160,
                            disabled=True,
                            key=f"extracted_{file_index}_{page.page_number}",
                        )
                    else:
                        st.caption(
                            f"ページ {page.page_number}: このページから文字情報は取得できませんでした。"
                        )

with step3:
    st.info("この機能は今後のPhaseで実装予定です。")

with step4:
    st.info("この機能は今後のPhaseで実装予定です。")

with step5:
    st.info("この機能は今後のPhaseで実装予定です。")
