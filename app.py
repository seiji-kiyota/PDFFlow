"""PDFFlow Ver1.0 Streamlit アプリケーション。"""

import pandas as pd
import streamlit as st

from pdf_flow.invoice_detail_parser import InvoiceDetails, parse_invoice_details
from pdf_flow.invoice_editor import (
    confirm_invoice,
    create_editable_basic,
    create_editable_details,
    detail_amount_total,
    detail_item_count,
    list_confirmed_invoices,
    reset_editable,
    resolve_status,
    sanitize_editor_rows,
    validate_invoice,
)
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


def clear_invoice_editor_state() -> None:
    """解析結果・編集中データ・確定データを破棄する。"""
    st.session_state.invoice_basic_infos = []
    st.session_state.invoice_parse_errors = []
    st.session_state.invoice_details = []
    st.session_state.invoice_detail_errors = []
    st.session_state.edited_basics = []
    st.session_state.edited_details = []
    st.session_state.invoice_statuses = []
    st.session_state.confirmed_invoices = []
    st.session_state.editor_revisions = []
    st.session_state.editor_source_identity = None


def initialize_editor_from_extractions(extractions: list[PdfTextExtraction]) -> None:
    """本文抽出結果から自動解析と編集用コピーを初期化する。"""
    parsed_basics: list[InvoiceBasicInfo] = []
    parse_errors: list[dict[str, str]] = []
    parsed_details: list[InvoiceDetails] = []
    detail_errors: list[dict[str, str]] = []

    for extraction in extractions:
        try:
            parsed_basics.append(
                parse_invoice_basic_info(extraction.filename, extraction.full_text)
            )
        except Exception:
            parse_errors.append(
                {
                    "filename": extraction.filename,
                    "error": "請求書基本情報を抽出できませんでした。",
                }
            )
            parsed_basics.append(
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
            parsed_details.append(
                parse_invoice_details(extraction.filename, extraction.full_text)
            )
        except Exception:
            detail_errors.append(
                {
                    "filename": extraction.filename,
                    "error": "請求明細を抽出できませんでした。",
                }
            )
            parsed_details.append(InvoiceDetails(filename=extraction.filename, items=()))

    st.session_state.invoice_basic_infos = parsed_basics
    st.session_state.invoice_parse_errors = parse_errors
    st.session_state.invoice_details = parsed_details
    st.session_state.invoice_detail_errors = detail_errors
    st.session_state.edited_basics = [create_editable_basic(info) for info in parsed_basics]
    st.session_state.edited_details = [
        create_editable_details(details) for details in parsed_details
    ]
    st.session_state.invoice_statuses = ["未確認"] * len(parsed_basics)
    st.session_state.confirmed_invoices = [None] * len(parsed_basics)
    st.session_state.editor_revisions = [0] * len(parsed_basics)
    st.session_state.editor_source_identity = tuple(
        (extraction.filename, extraction.page_count, len(extraction.full_text))
        for extraction in extractions
    )


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
if "edited_basics" not in st.session_state:
    st.session_state.edited_basics = []
if "edited_details" not in st.session_state:
    st.session_state.edited_details = []
if "invoice_statuses" not in st.session_state:
    st.session_state.invoice_statuses = []
if "confirmed_invoices" not in st.session_state:
    st.session_state.confirmed_invoices = []
if "editor_revisions" not in st.session_state:
    st.session_state.editor_revisions = []
if "editor_source_identity" not in st.session_state:
    st.session_state.editor_source_identity = None

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
        clear_invoice_editor_state()

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
            clear_invoice_editor_state()

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
    extracted_texts = st.session_state.extracted_texts

    if not extracted_texts:
        st.info("先に Step 2 でPDFを解析してください。")
    else:
        source_identity = tuple(
            (extraction.filename, extraction.page_count, len(extraction.full_text))
            for extraction in extracted_texts
        )
        if st.session_state.editor_source_identity != source_identity:
            initialize_editor_from_extractions(extracted_texts)

        confirmed_count = len(list_confirmed_invoices(st.session_state.confirmed_invoices))
        st.write(f"対象PDF: {len(extracted_texts)}件")
        st.write(f"確定済み: {confirmed_count}件")
        st.caption("自動抽出結果を確認し、必要な項目だけ修正して確定してください。")

        for item in st.session_state.invoice_parse_errors:
            st.error(f"{item['filename']}: {item['error']}")
        for item in st.session_state.invoice_detail_errors:
            st.error(f"{item['filename']}: {item['error']}")

        for index, parsed_basic in enumerate(st.session_state.invoice_basic_infos):
            parsed_details = st.session_state.invoice_details[index]
            revision = st.session_state.editor_revisions[index]
            edited_basic = st.session_state.edited_basics[index]
            status = resolve_status(
                edited_basic,
                st.session_state.edited_details[index],
                parsed_basic,
                parsed_details,
                st.session_state.confirmed_invoices[index],
            )
            st.session_state.invoice_statuses[index] = status

            with st.expander(f"{parsed_basic.filename}　[{status}]", expanded=True):
                if status == "確定済み":
                    st.success(f"状態: {status}")
                elif status == "編集中":
                    st.warning(f"状態: {status}")
                else:
                    st.info(f"状態: {status}")

                st.markdown("**基本情報**")
                edited_basic["customer_name"] = st.text_input(
                    "取引先名",
                    value=str(edited_basic.get("customer_name") or ""),
                    key=f"customer_name_{index}_{revision}",
                )
                edited_basic["customer_address"] = st.text_input(
                    "取引先住所",
                    value=str(edited_basic.get("customer_address") or ""),
                    key=f"customer_address_{index}_{revision}",
                )
                edited_basic["invoice_number"] = st.text_input(
                    "請求書番号",
                    value=str(edited_basic.get("invoice_number") or ""),
                    key=f"invoice_number_{index}_{revision}",
                )
                date_cols = st.columns(2)
                with date_cols[0]:
                    edited_basic["invoice_date"] = st.text_input(
                        "請求日 (YYYY-MM-DD)",
                        value=str(edited_basic.get("invoice_date") or ""),
                        key=f"invoice_date_{index}_{revision}",
                    )
                with date_cols[1]:
                    edited_basic["due_date"] = st.text_input(
                        "支払期限 (YYYY-MM-DD)",
                        value=str(edited_basic.get("due_date") or ""),
                        key=f"due_date_{index}_{revision}",
                    )
                amount_cols = st.columns(3)
                with amount_cols[0]:
                    edited_basic["subtotal"] = st.number_input(
                        "税抜金額",
                        value=edited_basic.get("subtotal"),
                        step=1,
                        key=f"subtotal_{index}_{revision}",
                    )
                with amount_cols[1]:
                    edited_basic["tax"] = st.number_input(
                        "消費税",
                        value=edited_basic.get("tax"),
                        step=1,
                        key=f"tax_{index}_{revision}",
                    )
                with amount_cols[2]:
                    edited_basic["total"] = st.number_input(
                        "請求金額（税込）",
                        value=edited_basic.get("total"),
                        step=1,
                        key=f"total_{index}_{revision}",
                    )
                st.session_state.edited_basics[index] = edited_basic

                st.markdown("**請求明細**")
                detail_df = pd.DataFrame(
                    st.session_state.edited_details[index],
                    columns=["品目", "数量", "単価", "明細金額"],
                )
                edited_df = st.data_editor(
                    detail_df,
                    num_rows="dynamic",
                    hide_index=True,
                    width="stretch",
                    key=f"details_editor_{index}_{revision}",
                    column_config={
                        "品目": st.column_config.TextColumn("品目"),
                        "数量": st.column_config.NumberColumn("数量", step=0.5),
                        "単価": st.column_config.NumberColumn("単価", step=1, format="%d"),
                        "明細金額": st.column_config.NumberColumn(
                            "明細金額", step=1, format="%d"
                        ),
                    },
                )
                edited_rows = sanitize_editor_rows(edited_df.to_dict("records"))
                st.session_state.edited_details[index] = edited_rows

                item_count = detail_item_count(edited_rows)
                amount_total = detail_amount_total(edited_rows)
                if item_count == 0:
                    st.warning("明細を取得できませんでした。")
                else:
                    st.write(f"明細件数: {item_count}件")
                    st.write(f"明細合計: {amount_total:,}円")

                subtotal = edited_basic.get("subtotal")
                if item_count == 0:
                    pass
                elif subtotal is None:
                    st.caption("税抜金額が未入力のため、明細合計との比較はできません。")
                elif amount_total == subtotal:
                    st.success("明細合計と税抜金額は一致しています。")
                else:
                    st.warning("明細合計と税抜金額が一致しません。")

                live_result = validate_invoice(edited_basic, edited_rows)
                for warning in live_result.warnings:
                    st.warning(warning)

                action_cols = st.columns(2)
                with action_cols[0]:
                    if st.button("自動抽出値に戻す", key=f"reset_{index}"):
                        reset_basic, reset_rows = reset_editable(
                            parsed_basic, parsed_details
                        )
                        st.session_state.edited_basics[index] = reset_basic
                        st.session_state.edited_details[index] = reset_rows
                        st.session_state.confirmed_invoices[index] = None
                        st.session_state.invoice_statuses[index] = "未確認"
                        st.session_state.editor_revisions[index] += 1
                        st.rerun()
                with action_cols[1]:
                    if st.button("この請求書を確定", key=f"confirm_{index}"):
                        confirmed, result = confirm_invoice(edited_basic, edited_rows)
                        if confirmed is None:
                            for error in result.errors:
                                st.error(error)
                        else:
                            st.session_state.confirmed_invoices[index] = confirmed
                            st.session_state.edited_basics[index] = create_editable_basic(
                                confirmed.basic
                            )
                            st.session_state.edited_details[index] = create_editable_details(
                                confirmed.details
                            )
                            st.session_state.invoice_statuses[index] = "確定済み"
                            st.session_state.editor_revisions[index] += 1
                            st.rerun()

                st.session_state.invoice_statuses[index] = resolve_status(
                    st.session_state.edited_basics[index],
                    st.session_state.edited_details[index],
                    parsed_basic,
                    parsed_details,
                    st.session_state.confirmed_invoices[index],
                )

with step4:
    st.info("この機能は今後のPhaseで実装予定です。")

with step5:
    st.info("この機能は今後のPhaseで実装予定です。")
