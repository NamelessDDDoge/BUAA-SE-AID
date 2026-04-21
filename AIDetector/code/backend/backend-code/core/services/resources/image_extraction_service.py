import io
import os
import shutil
import uuid
import zipfile
from pathlib import Path

from PIL import Image
from django.conf import settings

from ...models import ImageUpload


EXTRACTED_IMAGE_DIR = "extracted_images"


def create_image_uploads_for_resource(file_management):
    stored_path = (file_management.stored_path or "").strip()
    if not stored_path:
        return []

    file_ext = Path(file_management.file_name or stored_path).suffix.lower()
    if file_ext == ".pdf":
        return extract_images_from_pdf(file_management, stored_path)
    if file_ext == ".zip":
        return extract_images_from_zip(file_management, stored_path)
    return [store_uploaded_image(file_management, stored_path)]


def extract_images_from_pdf(file_management, relative_file_path):
    import fitz

    created_images = []
    full_file_path = _media_path(relative_file_path)
    with fitz.open(full_file_path) as pdf_document:
        for page_index in range(pdf_document.page_count):
            page = pdf_document.load_page(page_index)
            try:
                for image_index, image_meta in enumerate(page.get_images(full=True)):
                    base_image = pdf_document.extract_image(image_meta[0])
                    image_filename = (
                        f"{file_management.id}_page{page_index + 1}_image{image_index + 1}.{base_image['ext']}"
                    )
                    relative_image_path = _save_image_bytes(base_image["image"], image_filename)
                    created_images.append(
                        ImageUpload.objects.create(
                            file_management=file_management,
                            image=relative_image_path,
                            extracted_from_pdf=True,
                            page_number=page_index + 1,
                            isDetect=False,
                            isReview=False,
                            isFake=False,
                        )
                    )
            finally:
                del page
    return created_images


def extract_images_from_zip(file_management, relative_file_path):
    created_images = []
    full_file_path = _media_path(relative_file_path)
    with zipfile.ZipFile(full_file_path) as archive:
        for member_name in archive.namelist():
            member_info = archive.getinfo(member_name)
            if member_info.is_dir():
                continue

            lower_name = member_name.lower()
            if lower_name.endswith((".png", ".jpg", ".jpeg")):
                try:
                    image_data = archive.read(member_name)
                    image_name = f"{file_management.id}_{os.path.basename(member_name)}"
                    relative_image_path = _save_pillow_image(Image.open(io.BytesIO(image_data)), image_name)
                    created_images.append(
                        ImageUpload.objects.create(
                            file_management=file_management,
                            image=relative_image_path,
                            extracted_from_pdf=False,
                            isDetect=False,
                            isReview=False,
                            isFake=False,
                        )
                    )
                except Exception:
                    continue
            elif lower_name.endswith(".pdf"):
                temp_relative_path = _write_temp_pdf(archive.read(member_name))
                try:
                    created_images.extend(extract_images_from_pdf(file_management, temp_relative_path))
                finally:
                    _remove_media_file(temp_relative_path)
    return created_images


def store_uploaded_image(file_management, relative_file_path):
    source_path = _media_path(relative_file_path)
    suffix = Path(relative_file_path).suffix or ".bin"
    relative_image_path = _build_image_relative_path(
        file_management_id=file_management.id,
        suffix=suffix,
        hint="upload",
    )
    target_path = _media_path(relative_image_path)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copyfile(source_path, target_path)
    return ImageUpload.objects.create(
        file_management=file_management,
        image=relative_image_path,
        extracted_from_pdf=False,
        isDetect=False,
        isReview=False,
        isFake=False,
    )


def _save_image_bytes(image_data, image_name):
    return _save_pillow_image(Image.open(io.BytesIO(image_data)), image_name)


def _save_pillow_image(image, image_name):
    relative_path = _build_image_relative_path(
        file_management_id=_extract_file_management_id(image_name),
        suffix=Path(image_name).suffix or ".png",
        hint=Path(image_name).stem,
    )
    full_path = _media_path(relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    image.save(full_path)
    return relative_path


def _write_temp_pdf(pdf_data):
    relative_path = os.path.join("temp_pdfs", f"{uuid.uuid4().hex}.pdf").replace("\\", "/")
    full_path = _media_path(relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as handle:
        handle.write(pdf_data)
    return relative_path


def _remove_media_file(relative_path):
    full_path = _media_path(relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)


def _build_image_relative_path(*, file_management_id, suffix, hint):
    max_length = ImageUpload._meta.get_field("image").max_length
    normalized_suffix = _normalize_suffix(suffix)
    normalized_hint = _sanitize_hint(hint)
    unique_name = f"{file_management_id}_{normalized_hint}_{uuid.uuid4().hex}{normalized_suffix}"
    relative_path = os.path.join(EXTRACTED_IMAGE_DIR, unique_name).replace("\\", "/")

    if len(relative_path) <= max_length:
        return relative_path

    available_hint_length = max_length - len(os.path.join(EXTRACTED_IMAGE_DIR, "").replace("\\", "/")) - len(
        f"{file_management_id}__{uuid.uuid4().hex}{normalized_suffix}"
    )
    trimmed_hint = normalized_hint[: max(available_hint_length, 0)]
    fallback_name = f"{file_management_id}_{trimmed_hint}_{uuid.uuid4().hex}{normalized_suffix}".replace("__", "_")
    return os.path.join(EXTRACTED_IMAGE_DIR, fallback_name).replace("\\", "/")


def _extract_file_management_id(image_name):
    stem_prefix = Path(image_name).stem.split("_", 1)[0]
    try:
        return int(stem_prefix)
    except ValueError:
        return 0


def _normalize_suffix(suffix):
    normalized = (suffix or ".png").strip()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    return normalized[:10]


def _sanitize_hint(hint):
    raw_hint = "".join(char if char.isalnum() else "_" for char in (hint or "image"))
    compact_hint = "_".join(part for part in raw_hint.split("_") if part)
    return compact_hint[:24] or "image"


def _media_path(relative_path):
    return os.path.join(settings.MEDIA_ROOT, relative_path)
