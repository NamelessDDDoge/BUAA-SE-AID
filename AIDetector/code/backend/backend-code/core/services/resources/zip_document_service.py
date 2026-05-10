import mimetypes
import os
import re
import zipfile
from pathlib import PurePosixPath

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.text import get_valid_filename


MAX_ZIP_SIZE = 100 * 1024 * 1024
MAX_ENTRY_SIZE = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 1000
MAX_CANDIDATES = 300
ZIP_UTF8_FLAG = 0x800
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
MOJIBAKE_PATTERN = re.compile(r"[├-╬│─┌-┘┼┤┴┬└┐└┘╔-╝▒▓░]")

ZIP_CONTEXT_ALLOWED_EXTENSIONS = {
    "paper": {".pdf", ".docx", ".txt"},
    "review-paper": {".pdf", ".docx", ".txt"},
    "review-file": {".pdf", ".docx", ".txt"},
}


def get_allowed_zip_extensions(context):
    try:
        return ZIP_CONTEXT_ALLOWED_EXTENSIONS[context]
    except KeyError as exc:
        raise ValueError("Invalid ZIP upload context") from exc


def list_document_entries(uploaded_zip, context):
    _validate_zip_file(uploaded_zip)
    allowed_extensions = get_allowed_zip_extensions(context)
    entries = []
    seen_entry_names = set()

    try:
        uploaded_zip.seek(0)
        with zipfile.ZipFile(uploaded_zip) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise ValueError("ZIP 文件条目过多，请精简后重新上传。")

            for info in infos:
                normalized_name = _normalize_zip_info_name(info)
                if not normalized_name or normalized_name in seen_entry_names or info.is_dir():
                    continue

                file_ext = os.path.splitext(normalized_name)[1].lower()
                if file_ext not in allowed_extensions:
                    continue
                if info.file_size > MAX_ENTRY_SIZE:
                    continue

                seen_entry_names.add(normalized_name)
                file_name = _get_entry_file_name(normalized_name)
                display_name = _get_entry_display_name(normalized_name)
                entries.append(
                    {
                        "entry_name": normalized_name,
                        "file_name": file_name,
                        "display_name": display_name,
                        "display_path": normalized_name,
                        "file_ext": file_ext.lstrip("."),
                        "file_size": info.file_size,
                        "compressed_size": info.compress_size,
                        "content_type": _guess_content_type(file_name),
                    }
                )

                if len(entries) >= MAX_CANDIDATES:
                    break
    except zipfile.BadZipFile as exc:
        raise ValueError("ZIP 文件无法读取或已损坏。") from exc
    finally:
        try:
            uploaded_zip.seek(0)
        except Exception:
            pass

    return entries


def build_uploaded_file_from_zip_entry(uploaded_zip, entry_name, context):
    _validate_zip_file(uploaded_zip)
    requested_name = _normalize_zip_entry_name(entry_name)
    if not requested_name:
        raise ValueError("Invalid ZIP entry_name")

    allowed_extensions = get_allowed_zip_extensions(context)
    file_ext = os.path.splitext(requested_name)[1].lower()
    if file_ext not in allowed_extensions:
        raise ValueError("所选 ZIP 内文件格式不符合当前上传入口要求。")

    try:
        uploaded_zip.seek(0)
        with zipfile.ZipFile(uploaded_zip) as archive:
            target_info = None
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise ValueError("ZIP 文件条目过多，请精简后重新上传。")

            for info in infos:
                if info.is_dir():
                    continue
                if _normalize_zip_info_name(info) == requested_name:
                    target_info = info
                    break

            if target_info is None:
                raise ValueError("所选文件不存在于 ZIP 压缩包中。")
            if target_info.file_size > MAX_ENTRY_SIZE:
                raise ValueError("所选 ZIP 内文件超过 100MB 限制。")

            with archive.open(target_info) as extracted_file:
                payload = extracted_file.read(MAX_ENTRY_SIZE + 1)
            if len(payload) > MAX_ENTRY_SIZE:
                raise ValueError("所选 ZIP 内文件超过 100MB 限制。")
    except zipfile.BadZipFile as exc:
        raise ValueError("ZIP 文件无法读取或已损坏。") from exc
    finally:
        try:
            uploaded_zip.seek(0)
        except Exception:
            pass

    file_name = _get_entry_file_name(requested_name)
    return SimpleUploadedFile(
        file_name,
        payload,
        content_type=_guess_content_type(file_name),
    )


def _validate_zip_file(uploaded_zip):
    if uploaded_zip is None:
        raise ValueError("file is required")
    if uploaded_zip.size > MAX_ZIP_SIZE:
        raise ValueError("File size exceeds 100MB limit")

    file_ext = os.path.splitext(uploaded_zip.name or "")[1].lower()
    if file_ext != ".zip":
        raise ValueError("请上传 ZIP 压缩包。")


def _normalize_zip_entry_name(entry_name):
    name = str(entry_name or "").replace("\\", "/").strip()
    if not name or name.startswith("/") or name.startswith("../") or "/../" in name:
        return ""

    path = PurePosixPath(name)
    parts = path.parts
    if not parts:
        return ""
    if any(part in {"", ".", ".."} for part in parts):
        return ""
    if any(_looks_like_windows_drive(part) for part in parts):
        return ""

    return "/".join(parts)


def _normalize_zip_info_name(info):
    return _normalize_zip_entry_name(_decode_zip_info_filename(info))


def _decode_zip_info_filename(info):
    filename = str(info.filename or "")
    if info.flag_bits & ZIP_UTF8_FLAG:
        return filename

    try:
        raw_name = filename.encode("cp437")
    except UnicodeEncodeError:
        return filename

    for encoding in ("utf-8", "gbk", "cp936", "big5"):
        try:
            decoded = raw_name.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _is_better_decoded_name(filename, decoded):
            return decoded
    return filename


def _is_better_decoded_name(original, decoded):
    if not decoded or decoded == original:
        return False
    if CJK_PATTERN.search(decoded):
        return True
    return bool(MOJIBAKE_PATTERN.search(original) and not MOJIBAKE_PATTERN.search(decoded))


def _looks_like_windows_drive(part):
    return len(part) == 2 and part[1] == ":" and part[0].isalpha()


def _get_entry_file_name(entry_name):
    file_name = PurePosixPath(entry_name).name
    safe_name = get_valid_filename(file_name)
    return safe_name or "selected_document"


def _get_entry_display_name(entry_name):
    return PurePosixPath(entry_name).name


def _guess_content_type(file_name):
    return mimetypes.guess_type(file_name)[0] or "application/octet-stream"
