import os
import json
import mimetypes
import subprocess
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader, PdfWriter
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions


def _get_env() -> Dict[str, str]:
    return {
        "PROJECT_ID": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "LOCATION": os.getenv("DOC_AI_LOCATION", "us"),
        "PROCESSOR_ID": os.getenv("DOC_AI_PROCESSOR_ID"),
        "BUCKET": os.getenv("DOC_AI_GCS_BUCKET"),
        "PREFIX": os.getenv("DOC_AI_GCS_PREFIX", "docai"),
        "LIBREOFFICE": os.getenv("LIBREOFFICE_PATH", r"C:\\Program Files\\LibreOffice\\program\\soffice.exe"),
    }


ALLOWED_PDF = {"application/pdf"}
ALLOWED_PPT = {
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
LOW_TEXT_THRESHOLD = 200


def _ppt_to_pdf(in_path: str, soffice: str) -> str:
    if not os.path.exists(soffice):
        raise RuntimeError("PPT→PDF 변환에 LibreOffice가 필요합니다. LIBREOFFICE_PATH를 설정하세요")
    out_dir = os.path.dirname(in_path)
    cmd = [soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", out_dir, in_path]
    subprocess.run(cmd, check=True)
    pdf_path = os.path.splitext(in_path)[0] + ".pdf"
    if not os.path.exists(pdf_path):
        raise RuntimeError("PPT→PDF 변환 실패")
    return pdf_path


def _count_pdf_pages(pdf_path: str) -> int:
    with open(pdf_path, "rb") as f:
        return len(PdfReader(f).pages)


def _text_from_anchor(doc_text: str, text_anchor) -> str:
    if not text_anchor or not getattr(text_anchor, "text_segments", None):
        return ""
    out: List[str] = []
    for seg in text_anchor.text_segments:
        start = int(seg.start_index) if seg.start_index is not None else 0
        end = int(seg.end_index)
        out.append(doc_text[start:end])
    return "".join(out)


def _layout_text(doc_text: str, layout) -> str:
    return _text_from_anchor(doc_text, layout.text_anchor) if layout else ""


def _table_to_markdown(doc_text: str, table) -> str:
    header_rows, body_rows = [], []
    for hr in getattr(table, "header_rows", []):
        header_rows.append([_layout_text(doc_text, c.layout).strip().replace("\n", " ") for c in hr.cells])
    for br in getattr(table, "body_rows", []):
        body_rows.append([_layout_text(doc_text, c.layout).strip().replace("\n", " ") for c in br.cells])

    md: List[str] = []
    if header_rows:
        header = header_rows[0]
        md.append("| " + " | ".join(header) + " |")
        md.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in (body_rows or header_rows[1:]):
        md.append("| " + " | ".join(row) + " |")
    return "\n".join(md)


def _pages_summary(doc) -> Tuple[List[Dict[str, Any]], List[int], int]:
    full_text = doc.text or ""
    pages_info: List[Dict[str, Any]] = []
    low_text_pages: List[int] = []
    tables_total = 0
    for idx, page in enumerate(getattr(doc, "pages", [])):
        ptext = _layout_text(full_text, page.layout)
        char_count = len(ptext)
        word_count = len(ptext.split())
        low = char_count < LOW_TEXT_THRESHOLD

        md_tables: List[str] = []
        for t in getattr(page, "tables", []):
            tables_total += 1
            try:
                md_tables.append(_table_to_markdown(full_text, t))
            except Exception:
                pass

        if low:
            low_text_pages.append(idx + 1)

        pages_info.append({
            "index": idx + 1,
            "text": ptext,
            "char_count": char_count,
            "word_count": word_count,
            "low_text": low,
            "tables_markdown": md_tables,
        })
    return pages_info, low_text_pages, tables_total


def _process_online(pdf_path: str, env: Dict[str, str], *, imageless: bool = False) -> Dict[str, Any]:
    opts = ClientOptions(api_endpoint=f"{env['LOCATION']}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(env["PROJECT_ID"], env["LOCATION"], env["PROCESSOR_ID"])

    with open(pdf_path, "rb") as f:
        raw_document = documentai.RawDocument(content=f.read(), mime_type="application/pdf")

    # 이미지/도표 텍스트 포함 여부는 imageless 플래그로 제어
    result = client.process_document(request={
        "name": name,
        "raw_document": raw_document,
        "imageless_mode": imageless,
    })
    doc = result.document
    full_text = doc.text or ""
    pages_info, low_text_pages, tables_total = _pages_summary(doc)

    return {
        "full_text": full_text,
        "pages": pages_info,
        "low_text_pages": low_text_pages,
        "tables_total": tables_total,
    }


def _process_online_split(pdf_path: str, env: Dict[str, str], *, chunk_pages: int = 15, imageless: bool = False) -> Dict[str, Any]:
    """30페이지 초과 문서를 chunk_pages 단위로 잘라 처리 후 병합.
    - 온라인 API 제한(<=30p) 우회를 위한 분할 처리
    - 페이지 인덱스는 1-base 유지, 누적 offset 적용
    """
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    full_text_concat: List[str] = []
    merged_pages: List[Dict[str, Any]] = []
    merged_low: List[int] = []
    tables_total = 0

    offset = 0
    import tempfile, os
    for start in range(0, total_pages, chunk_pages):
        end = min(start + chunk_pages, total_pages)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with open(tmp_path, "wb") as f:
                writer.write(f)

            part = _process_online(tmp_path, env, imageless=imageless)

            # full_text 병합
            full_text_concat.append(part.get("full_text", ""))

            # 페이지 메타 병합 (인덱스 보정)
            for p in part.get("pages", []):
                p2 = dict(p)
                p2["index"] = p.get("index", 1) + offset
                merged_pages.append(p2)

            # 저텍스트 페이지 병합 (오프셋 적용)
            merged_low.extend([(lp + offset) for lp in part.get("low_text_pages", [])])

            # 표 개수 누적
            tables_total += int(part.get("tables_total", 0))

            offset += (end - start)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    preview = "".join(full_text_concat)
    return {
        "full_text": preview,
        "pages": merged_pages,
        "low_text_pages": sorted(set(merged_low)),
        "tables_total": tables_total,
    }


def extract_document(file_path: str) -> Dict[str, Any]:
    env = _get_env()
    if not env["PROJECT_ID"] or not env["PROCESSOR_ID"]:
        raise RuntimeError("DOC_AI 설정 누락: GOOGLE_CLOUD_PROJECT/DOC_AI_PROCESSOR_ID 확인")

    mime, _ = mimetypes.guess_type(file_path)
    in_path = file_path

    if mime in ALLOWED_PPT:
        in_path = _ppt_to_pdf(file_path, env["LIBREOFFICE"])
        mime = "application/pdf"
    if mime not in ALLOWED_PDF:
        raise ValueError(f"지원하지 않는 MIME: {mime}")

    pages = _count_pdf_pages(in_path)
    # 문서 크기에 따라 모드/분할 전략 결정
    # - non-imageless(이미지 포함) 최대 15p 제한
    # - imageless(True) 최대 30p 허용 (이미지 텍스트 제외)
    if pages <= 15:
        return _process_online(in_path, env, imageless=False)
    if pages <= 30:
        return _process_online_split(in_path, env, chunk_pages=15, imageless=False)
    return _process_online_split(in_path, env, chunk_pages=15, imageless=False)

