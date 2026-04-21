import io
import os
import uuid
import zipfile

from PIL import Image
from django.conf import settings
from django.core.files.storage import FileSystemStorage

from ...models import FileManagement, ImageUpload


def save_uploaded_resource(*, user, uploaded_file, detection_type, review_role="", linked_paper_file_id=None):
    if uploaded_file is None:
        raise ValueError("file is required")

    valid_detection_types = {"image", "paper", "review"}
    if detection_type not in valid_detection_types:
        raise ValueError("Invalid detection_type")

    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    max_size = 100 * 1024 * 1024
    if uploaded_file.size > max_size:
        raise ValueError("File size exceeds 100MB limit")

    allowed_image_ext = {".png", ".jpg", ".jpeg", ".zip"}
    allowed_paper_ext = {".docx", ".pdf", ".zip"}
    allowed_review_ext = {".docx", ".pdf", ".txt", ".zip"}

    linked_paper_file = None
    if detection_type == "image":
        if file_ext not in allowed_image_ext:
            raise ValueError("Unsupported image file format")
    elif detection_type == "paper":
        if file_ext not in allowed_paper_ext:
            raise ValueError("Unsupported paper file format")
    else:
        if review_role not in {"paper", "review"}:
            raise ValueError("review_role must be paper or review")

        if review_role == "paper":
            if file_ext not in allowed_paper_ext:
                raise ValueError("Unsupported review-paper file format")
        else:
            if file_ext not in allowed_review_ext:
                raise ValueError("Unsupported review file format")
            if not linked_paper_file_id:
                raise ValueError("Review upload must include linked_paper_file_id")

            try:
                linked_paper_file = FileManagement.objects.get(id=linked_paper_file_id, user=user)
            except FileManagement.DoesNotExist as exc:
                raise FileNotFoundError("Linked paper file not found") from exc

            if linked_paper_file.resource_type != "review_paper":
                raise ValueError("linked_paper_file_id is not a review paper file")

    if detection_type == "image":
        resource_type = "image"
    elif detection_type == "paper":
        resource_type = "paper"
    elif review_role == "paper":
        resource_type = "review_paper"
    else:
        resource_type = "review_file"

    file_management = FileManagement.objects.create(
        organization=user.organization,
        user=user,
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        file_type=uploaded_file.content_type or "application/octet-stream",
        resource_type=resource_type,
        linked_file=linked_paper_file,
    )

    unique_filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    file_storage = FileSystemStorage()
    stored_path = file_storage.save(f"uploads/{unique_filename}", uploaded_file)
    file_url = file_storage.url(stored_path)

    file_management.stored_path = stored_path
    file_management.save(update_fields=["stored_path"])

    if detection_type == "image":
        if file_ext == ".pdf":
            _extract_images_from_pdf(file_management, stored_path)
        elif file_ext == ".zip":
            _extract_images_from_zip(file_management, uploaded_file)
        else:
            _store_image(file_management, uploaded_file)

    return {
        "file_id": file_management.id,
        "file_url": file_url,
        "detection_type": detection_type,
        "resource_type": resource_type,
        "linked_paper_file_id": linked_paper_file.id if linked_paper_file else None,
    }


def _extract_images_from_pdf(file_management, file_path):
    import fitz

    full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
    with fitz.open(full_file_path) as pdf_document:
        for page_number in range(pdf_document.page_count):
            page = pdf_document.load_page(page_number)
            try:
                image_list = page.get_images(full=True)
                for image_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_filename = (
                        f"{file_management.id}_page{page_number + 1}_image{image_index + 1}.{image_ext}"
                    )

                    relative_image_path = _save_pdf_image(image_bytes, image_filename)
                    ImageUpload.objects.create(
                        file_management=file_management,
                        image=relative_image_path,
                        extracted_from_pdf=True,
                        page_number=page_number + 1,
                        isDetect=False,
                        isReview=False,
                        isFake=False,
                    )
            finally:
                del page


def _extract_images_from_zip(file_management, uploaded_file):
    with zipfile.ZipFile(uploaded_file) as zip_file:
        for file_name in zip_file.namelist():
            file_info = zip_file.getinfo(file_name)
            if file_info.is_dir():
                continue

            if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    img_data = zip_file.read(file_name)
                    image = Image.open(io.BytesIO(img_data))
                    image_name = f"{file_management.id}_{os.path.basename(file_name)}"
                    relative_image_path = _save_zip_image(image, image_name)
                    ImageUpload.objects.create(
                        file_management=file_management,
                        image=relative_image_path,
                        extracted_from_pdf=False,
                        isDetect=False,
                        isReview=False,
                        isFake=False,
                    )
                except Exception:
                    continue
            elif file_name.lower().endswith(".pdf"):
                temp_pdf_path = None
                try:
                    pdf_data = zip_file.read(file_name)
                    temp_pdf_dir = os.path.join(settings.MEDIA_ROOT, "temp_pdfs")
                    os.makedirs(temp_pdf_dir, exist_ok=True)
                    temp_pdf_filename = f"{uuid.uuid4().hex}.pdf"
                    temp_pdf_path = os.path.join(temp_pdf_dir, temp_pdf_filename)
                    with open(temp_pdf_path, "wb") as handle:
                        handle.write(pdf_data)
                    relative_temp_pdf_path = os.path.join("temp_pdfs", temp_pdf_filename)
                    _extract_images_from_pdf(file_management, relative_temp_pdf_path)
                finally:
                    if temp_pdf_path and os.path.exists(temp_pdf_path):
                        try:
                            os.remove(temp_pdf_path)
                        except Exception:
                            pass


def _save_pdf_image(image_data, image_name):
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join("extracted_images", unique_image_name).replace("\\", "/")
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    image = Image.open(io.BytesIO(image_data))
    image.save(full_path)
    return relative_path


def _save_zip_image(image, image_name):
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join("extracted_images", unique_image_name).replace("\\", "/")
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    image.save(full_path)
    return relative_path


def _store_image(file_management, uploaded_file):
    unique_filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    relative_path = os.path.join("extracted_images", f"{file_management.id}_{unique_filename}").replace("\\", "/")
    file_storage = FileSystemStorage()
    file_storage.save(relative_path, uploaded_file)

    ImageUpload.objects.create(
        file_management=file_management,
        image=relative_path,
        extracted_from_pdf=False,
        isDetect=False,
        isReview=False,
        isFake=False,
    )
