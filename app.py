"""PDFFlow Ver1.0 Streamlit アプリケーション。"""

import streamlit as st

from pdf_flow.invoice_detail_parser import InvoiceDetails, parse_invoice_details
from pdf_flow.invoice_parser import InvoiceBasicInfo, parse_invoice_basic_info
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
if "invoice_basic_infos" not in st.session_state:
    st.session_state.invoice_basic_infos = []
if "invoice_parse_errors" not in st.session_state:
    st.session_state.invoice_parse_errors = []
if "invoice_details" not in st.session_state:
    st.session_state.invoice_details = []
if "invoice_detail_errors" not in st.session_state:
    st.session_state.invoice_detail_errors = []

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
        st.session_state.invoice_basic_infos = []
        st.session_state.invoice_parse_errors = []
        st.session_state.invoice_details = []
        st.session_state.invoice_detail_errors = []

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
            st.session_state.invoice_basic_infos = []
            st.session_state.invoice_parse_errors = []
            st.session_state.invoice_details = []
            st.session_state.invoice_detail_errors = []

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


def format_extracted_value(value: str | int | float | None) -> str:
    """抽出値を画面表示用の文字列へ変換する。"""
    if value is None or value == "":
        return "未取得"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return str(value)
    return str(value)


with step3:
    extracted_texts = st.session_state.extracted_texts

    if not extracted_texts:
        st.info("先に Step 2 でPDFを解析してください。")
    else:
        st.write(f"対象PDF: {len(extracted_texts)}件")
        st.caption("抽出した本文から請求書の基本情報と明細を表示します。")

        invoice_basic_infos: list[InvoiceBasicInfo] = []
        invoice_parse_errors: list[dict[str, str]] = []
        invoice_details_list: list[InvoiceDetails] = []
        invoice_detail_errors: list[dict[str, str]] = []
        for extraction in extracted_texts:
            try:
                invoice_basic_infos.append(
                    parse_invoice_basic_info(extraction.filename, extraction.full_text)
                )
            except Exception:
                invoice_parse_errors.append(
                    {
                        "filename": extraction.filename,
                        "error": "請求書基本情報を抽出できませんでした。",
                    }
                )
                invoice_basic_infos.append(
                    InvoiceBasicInfo(
                        filename=extraction.filename,
                        customer_name=None,
                        customer_address=None,
                        invoice_number=None,
                        invoice_date=None,
                        due_date=None,
                        subtotal=None,
                        tax=None,
                        total=None,
                    )
                )
            try:
                invoice_details_list.append(
                    parse_invoice_details(extraction.filename, extraction.full_text)
                )
            except Exception:
                invoice_detail_errors.append(
                    {
                        "filename": extraction.filename,
                        "error": "請求明細を抽出できませんでした。",
                    }
                )
                invoice_details_list.append(
                    InvoiceDetails(filename=extraction.filename, items=())
                )
        st.session_state.invoice_basic_infos = invoice_basic_infos
        st.session_state.invoice_parse_errors = invoice_parse_errors
        st.session_state.invoice_details = invoice_details_list
        st.session_state.invoice_detail_errors = invoice_detail_errors

        for item in invoice_parse_errors:
            st.error(f"{item['filename']}: {item['error']}")
        for item in invoice_detail_errors:
            st.error(f"{item['filename']}: {item['error']}")

        for info, details in zip(invoice_basic_infos, invoice_details_list, strict=True):
            with st.expander(info.filename, expanded=True):
                st.markdown("**基本情報**")
                rows = [
                    {"項目": "取引先名", "値": format_extracted_value(info.customer_name)},
                    {"項目": "取引先住所", "値": format_extracted_value(info.customer_address)},
                    {"項目": "請求書番号", "値": format_extracted_value(info.invoice_number)},
                    {"項目": "請求日", "値": format_extracted_value(info.invoice_date)},
                    {"項目": "支払期限", "値": format_extracted_value(info.due_date)},
                    {"項目": "税抜金額", "値": format_extracted_value(info.subtotal)},
                    {"項目": "消費税", "値": format_extracted_value(info.tax)},
                    {"項目": "請求金額（税込）", "値": format_extracted_value(info.total)},
                ]
                st.dataframe(rows, hide_index=True, width="stretch")

                st.markdown("**請求明細**")
                if details.item_count() == 0:
                    st.warning("明細を取得できませんでした。")
                else:
                    st.write(f"明細件数: {details.item_count()}件")
                    st.write(f"明細合計: {details.amount_total():,}円")
                    if info.subtotal is None:
                        st.caption("税抜金額が未取得のため、明細合計との比較はできません。")
                    elif details.amount_total() == info.subtotal:
                        st.success("明細合計と税抜金額は一致しています。")
                    else:
                        st.warning("明細合計と税抜金額が一致しません。")
                    detail_rows = [
                        {
                            "品目": item.item_name,
                            "数量": format_extracted_value(item.quantity),
                            "単価": format_extracted_value(item.unit_price),
                            "明細金額": format_extracted_value(item.amount),
                        }
                        for item in details.items
                    ]
                    st.dataframe(detail_rows, hide_index=True, width="stretch")

with step4:
    st.info("この機能は今後のPhaseで実装予定です。")

with step5:
    st.info("この機能は今後のPhaseで実装予定です。")
