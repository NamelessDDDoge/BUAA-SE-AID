from pathlib import Path


UNREADABLE_FILE_MESSAGE = "无法读取文件内容，请上传可解析的文本文件。"
EMPTY_FILE_MESSAGE = "无内容"


def preprocess_document(file_path, max_segment_length=500, fallback_segment_length=2000):
    text_content = extract_document_text(file_path)
    paragraphs = extract_document_paragraphs(text_content)
    segments = split_text_into_segments(
        text_content,
        max_segment_length=max_segment_length,
        fallback_segment_length=fallback_segment_length,
    )
    return {
        "text_content": text_content,
        "paragraphs": paragraphs,
        "references": extract_document_references(text_content),
        "segments": segments,
    }


def extract_document_text(file_path):
    file_ext = Path(file_path).suffix.lower()
    try:
        if file_ext == ".pdf":
            import fitz

            with fitz.open(file_path) as document:
                return "".join(page.get_text() for page in document)
        if file_ext == ".docx":
            import docx

            document = docx.Document(file_path)
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        with open(file_path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception:
        try:
            with open(file_path, "r", encoding="gbk") as handle:
                return handle.read()
        except Exception:
            return UNREADABLE_FILE_MESSAGE


def split_text_into_segments(text_content, max_segment_length=500, fallback_segment_length=2000):
    paragraphs = extract_document_paragraphs(text_content)
    segments = []
    current_segment = ""

    for paragraph in paragraphs:
        if len(current_segment) + len(paragraph) < max_segment_length:
            current_segment += f"{paragraph} "
            continue

        if current_segment:
            segments.append(current_segment.strip())
        current_segment = f"{paragraph} "

    if current_segment:
        segments.append(current_segment.strip())

    if segments:
        return segments
    if text_content:
        return [text_content[:fallback_segment_length]]
    return [EMPTY_FILE_MESSAGE]


def extract_document_paragraphs(text_content):
    return [paragraph.strip() for paragraph in (text_content or "").split("\n") if paragraph.strip()]


def extract_document_references(text_content):
    paragraphs = extract_document_paragraphs(text_content)
    reference_heading_index = None
    for index, paragraph in enumerate(paragraphs):
        if paragraph.lower() in {"references", "bibliography", "参考文献"}:
            reference_heading_index = index
            break

    if reference_heading_index is not None:
        return paragraphs[reference_heading_index + 1 :]

    return [
        paragraph
        for paragraph in paragraphs
        if paragraph.startswith("[") or paragraph[:2].isdigit() or "doi" in paragraph.lower()
    ]
