import os
import uuid

from django.core.files.storage import FileSystemStorage

from ...models import FileManagement
from .image_extraction_service import create_image_uploads_for_resource


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
        create_image_uploads_for_resource(file_management)

    return {
        "file_id": file_management.id,
        "file_url": file_url,
        "detection_type": detection_type,
        "resource_type": resource_type,
        "linked_paper_file_id": linked_paper_file.id if linked_paper_file else None,
    }
