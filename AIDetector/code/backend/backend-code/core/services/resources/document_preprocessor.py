from pathlib import Path
import re

from .text_sanitizer import sanitize_text_content


UNREADABLE_FILE_MESSAGE = "无法读取文件内容，请上传可解析的文本文件。"
EMPTY_FILE_MESSAGE = "无内容"


def preprocess_document(file_path, max_segment_length=500, fallback_segment_length=2000):
    text_content = sanitize_text_content(extract_document_text(file_path))
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
        sentence_chunks = _split_paragraph_into_sentences(paragraph)
        for chunk in sentence_chunks:
            if len(chunk) > max_segment_length:
                for hard_chunk in _hard_split_text(chunk, max_segment_length):
                    if current_segment:
                        segments.append(current_segment.strip())
                        current_segment = ""
                    segments.append(hard_chunk.strip())
                continue

            if len(current_segment) + len(chunk) + 1 <= max_segment_length:
                current_segment = f"{current_segment} {chunk}".strip()
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = chunk

    if current_segment:
        segments.append(current_segment.strip())

    if segments:
        return segments
    if text_content:
        return [sanitize_text_content(text_content[:fallback_segment_length])]
    return [EMPTY_FILE_MESSAGE]


def extract_document_paragraphs(text_content):
    raw_text = sanitize_text_content(text_content or "")
    if not raw_text:
        return []

    normalized_text = re.sub(r"\r\n?", "\n", raw_text)
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)

    # Prefer blank lines as paragraph boundaries.
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized_text) if block.strip()]
    paragraphs = []
    for block in blocks:
        candidate_lines = [sanitize_text_content(line.strip()) for line in block.split("\n") if line.strip()]
        if len(candidate_lines) <= 1:
            paragraphs.append(block)
            continue

        merged_line = ""
        for line in candidate_lines:
            if not merged_line:
                merged_line = line
                continue

            # Start a new paragraph when encountering likely heading/item starts.
            if _looks_like_new_paragraph(line):
                paragraphs.append(merged_line.strip())
                merged_line = line
            else:
                merged_line = f"{merged_line} {line}".strip()
        if merged_line:
            paragraphs.append(merged_line.strip())

    return [p for p in paragraphs if p]


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


def _looks_like_new_paragraph(line):
    if re.match(r"^(第[一二三四五六七八九十0-9]+[章节部分]|[0-9]+[\.、])", line):
        return True
    if re.match(r"^\[[0-9]+\]", line):
        return True
    return False


def _split_paragraph_into_sentences(paragraph):
    text = sanitize_text_content(paragraph or "")
    if not text:
        return []

    parts = re.split(r"(?<=[。！？!?；;])\s+", text)
    refined = []
    for part in parts:
        cleaned = part.strip()
        if cleaned:
            refined.append(cleaned)
    return refined or [text]


def _hard_split_text(text, max_len):
    stripped = (text or "").strip()
    if not stripped:
        return []
    return [stripped[i: i + max_len] for i in range(0, len(stripped), max_len)]
