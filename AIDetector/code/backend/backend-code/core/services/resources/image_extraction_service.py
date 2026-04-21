import io
import os
import shutil
import uuid
import zipfile
from pathlib import Path

from PIL import Image
from django.conf import settings

from ...models import ImageUpload


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
    unique_filename = f"{file_management.id}_{uuid.uuid4().hex}_{Path(relative_file_path).name}"
    relative_image_path = os.path.join("extracted_images", unique_filename).replace("\\", "/")
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
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join("extracted_images", unique_image_name).replace("\\", "/")
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


def _media_path(relative_path):
    return os.path.join(settings.MEDIA_ROOT, relative_path)
