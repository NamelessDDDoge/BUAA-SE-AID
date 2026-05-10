from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
import os

from ..models import DetectionTask, FileManagement, ImageUpload, ResourceReviewRequest, User
from ..services import log_user_event
from ..services.resources import save_uploaded_resource
from ..services.resources.document_preprocessor import extract_document_paragraphs, preprocess_document
from ..services.resources.zip_document_service import (
    build_uploaded_file_from_zip_entry,
    list_document_entries,
)
from .views_dectection import CustomPagination


def _is_software_admin(user):
    return user.email == 'admin@mail.com' or (user.is_staff and user.organization is None)


def _can_access_file_record(user, file_management):
    if file_management.user_id == user.id:
        return True
    if not user.is_staff:
        return False
    if _is_software_admin(user):
        return True
    return user.organization_id is not None and user.organization_id == file_management.organization_id


def _can_access_detection_task(user, task):
    if task.user_id == user.id:
        return True
    if user.is_staff:
        if _is_software_admin(user):
            return True
        return user.organization_id is not None and user.organization_id == task.organization_id
    return ResourceReviewRequest.objects.filter(detection_task=task, reviewers=user).exists()


def _build_preview_response(
    *,
    file_management,
    text_content,
    source,
    paragraphs=None,
    segments=None,
    references=None,
):
    text_content = text_content or ""
    max_chars = 6000000  # 增加到 600 万字，避免因为截断导致用户上传截断后的 override_text
    truncated = len(text_content) > max_chars
    preview_text = text_content[:max_chars]
    paragraph_list = paragraphs if isinstance(paragraphs, list) else extract_document_paragraphs(preview_text)
    segment_list = segments if isinstance(segments, list) else paragraph_list
    reference_list = references if isinstance(references, list) else []

    return Response(
        {
            "file_id": file_management.id,
            "file_name": file_management.file_name,
            "resource_type": file_management.resource_type,
            "text_content": preview_text,
            "text_truncated": truncated,
            "text_source": source,
            "paragraph_count": len(paragraph_list),
            "segment_count": len(segment_list),
            "reference_count": len(reference_list),
            "paragraph_preview": paragraph_list[:8],
            "reference_preview": reference_list[:8],
        }
    )


def _get_task_preview_text(task, file_management):
    raw_results = task.text_detection_results if isinstance(task.text_detection_results, dict) else {}
    if file_management.resource_type == "review_file":
        override_text = raw_results.get("review_text_override") or raw_results.get("text_override")
        if isinstance(override_text, str) and override_text.strip():
            return override_text, "task_override"
        review_text = _join_result_text(raw_results.get("paragraph_results"))
        if review_text:
            return review_text, "task_results"
        review_text = _join_result_text(raw_results.get("relevance_results"), "review_text")
        if review_text:
            return review_text, "task_results"
        review_analysis = raw_results.get("review_analysis_results") or {}
        review_text = _join_result_text(review_analysis.get("paragraph_results"), "review_text")
        if review_text:
            return review_text, "task_results"
    if file_management.resource_type == "review_paper":
        override_text = raw_results.get("paper_text_override")
        if isinstance(override_text, str) and override_text.strip():
            return override_text, "task_override"
        return "", ""

    override_text = raw_results.get("paper_text_override") or raw_results.get("text_override")
    if isinstance(override_text, str) and override_text.strip():
        return override_text, "task_override"
    if file_management.resource_type == "paper":
        paper_text = _join_result_text(raw_results.get("paragraph_results"))
        if paper_text:
            return paper_text, "task_results"

    return "", ""


def _join_result_text(items, text_key="text"):
    if not isinstance(items, list):
        return ""
    parts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(text_key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n\n".join(parts)


def _resolve_zip_upload_context(detection_type, review_role, requested_context=""):
    if detection_type == "paper":
        resolved_context = "paper"
    elif detection_type == "review" and review_role == "paper":
        resolved_context = "review-paper"
    elif detection_type == "review" and review_role == "review":
        resolved_context = "review-file"
    else:
        raise ValueError("ZIP document selection only supports paper and Review uploads")

    if requested_context and requested_context != resolved_context:
        raise ValueError("ZIP upload context does not match detection_type/review_role")
    return resolved_context


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_file(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("upload"):
        return Response({"message": "Current user has no upload permission"}, status=403)

    detection_type = request.data.get("detection_type", "image")
    review_role = request.data.get("review_role", "")
    linked_paper_file_id = request.data.get("linked_paper_file_id")
    uploaded_file = request.FILES.get("file")

    try:
        upload_result = save_uploaded_resource(
            user=user,
            uploaded_file=uploaded_file,
            detection_type=detection_type,
            review_role=review_role,
            linked_paper_file_id=linked_paper_file_id,
        )
    except ValueError as exc:
        return Response({"message": str(exc)}, status=400)
    except FileNotFoundError as exc:
        return Response({"message": str(exc)}, status=404)

    log_user_event(
        user=request.user,
        operation_type="upload",
        related_model="FileManagement",
        related_id=upload_result["file_id"],
    )

    return Response({
        "message": "File uploaded successfully",
        **upload_result,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def list_zip_document_entries(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("upload"):
        return Response({"message": "Current user has no upload permission"}, status=403)

    uploaded_file = request.FILES.get("file")
    context = request.data.get("context", "")

    try:
        entries = list_document_entries(uploaded_file, context)
    except ValueError as exc:
        return Response({"message": str(exc)}, status=400)

    return Response(
        {
            "message": "ZIP entries loaded successfully",
            "zip_name": uploaded_file.name if uploaded_file else "",
            "context": context,
            "count": len(entries),
            "entries": entries,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_zip_document_entry(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("upload"):
        return Response({"message": "Current user has no upload permission"}, status=403)

    detection_type = request.data.get("detection_type", "image")
    review_role = request.data.get("review_role", "")
    linked_paper_file_id = request.data.get("linked_paper_file_id")
    context = request.data.get("context", "")
    entry_name = request.data.get("entry_name", "")
    uploaded_zip = request.FILES.get("file")

    try:
        resolved_context = _resolve_zip_upload_context(detection_type, review_role, context)
        extracted_file = build_uploaded_file_from_zip_entry(uploaded_zip, entry_name, resolved_context)
        upload_result = save_uploaded_resource(
            user=user,
            uploaded_file=extracted_file,
            detection_type=detection_type,
            review_role=review_role,
            linked_paper_file_id=linked_paper_file_id,
        )
    except ValueError as exc:
        return Response({"message": str(exc)}, status=400)
    except FileNotFoundError as exc:
        return Response({"message": str(exc)}, status=404)

    log_user_event(
        user=request.user,
        operation_type="upload",
        related_model="FileManagement",
        related_id=upload_result["file_id"],
    )

    return Response(
        {
            "message": "ZIP entry uploaded successfully",
            "source_zip_name": uploaded_zip.name if uploaded_zip else "",
            "selected_entry_name": entry_name,
            **upload_result,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_file_details(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    extracted_images = ImageUpload.objects.filter(file_management=file_management)
    image_urls = [image.image.url for image in extracted_images]

    return Response({
        "file_id": file_management.id,
        "user_id": file_management.user.id,
        "file_name": file_management.file_name,
        "file_url": file_management.file_size,
        "upload_time": timezone.localtime(file_management.upload_time),
        "is_pdf": file_management.file_type == "application/pdf",
        "extracted_images": image_urls,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_extracted_images(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    allowed_types = {"image", "paper", "review_paper", "review_file"}
    if file_management.resource_type not in allowed_types:
        return Response(
            {
                "message": "Current file type has no extracted images",
                "file_id": file_management.id,
                "resource_type": file_management.resource_type,
            },
            status=400,
        )

    extracted_images = ImageUpload.objects.filter(file_management=file_management).order_by("-id")
    paginator = CustomPagination()
    paginated_images = paginator.paginate_queryset(extracted_images, request)

    image_list = [
        {
            "image_id": image.id,
            "image_url": image.image.url,
            "page_number": image.page_number if image.extracted_from_pdf else None,
            "extracted_from_pdf": image.extracted_from_pdf,
            "isDetect": image.isDetect,
            "isReview": image.isReview,
            "isFake": image.isFake,
        }
        for image in paginated_images
    ]

    return Response({
        "file_id": file_management.id,
        "page": paginator.page.number,
        "page_size": paginator.get_page_size(request),
        "total": paginator.page.paginator.count,
        "images": image_list,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_uploaded_resource(request, file_id):
    try:
        file_management = FileManagement.objects.select_related("user", "organization").get(id=file_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    if not _can_access_file_record(request.user, file_management):
        return Response({"message": "Permission denied"}, status=403)

    stored_path = (file_management.stored_path or "").strip()
    if not stored_path:
        return Response({"message": "File path is empty", "file_id": file_management.id}, status=404)

    if stored_path.startswith(("http://", "https://")):
        return redirect(stored_path)

    file_path = stored_path if os.path.isabs(stored_path) else os.path.join(settings.MEDIA_ROOT, stored_path)
    if not os.path.isfile(file_path):
        return Response(
            {
                "message": "File is not available on the current server node. Sync the uploader's media/uploads directory to this deployment before downloading.",
                "file_id": file_management.id,
                "stored_path": stored_path,
            },
            status=404,
        )

    filename = file_management.file_name or os.path.basename(file_path)
    return FileResponse(open(file_path, "rb"), as_attachment=True, filename=filename)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_resource_text_preview(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    can_access = (
        file_management.user_id == request.user.id
        or request.user.is_staff
        or ResourceReviewRequest.objects.filter(selected_files=file_management, reviewers=request.user).exists()
    )
    if not can_access:
        return Response({"message": "File not found"}, status=404)

    if file_management.resource_type not in {"paper", "review_paper", "review_file"}:
        return Response(
            {
                "message": "Current file type has no text preview",
                "file_id": file_management.id,
                "resource_type": file_management.resource_type,
            },
            status=400,
        )

    task_id = request.query_params.get("task_id")
    if task_id:
        try:
            task = DetectionTask.objects.prefetch_related("resource_files").get(id=task_id)
        except (DetectionTask.DoesNotExist, ValueError):
            return Response({"message": "Detection task not found"}, status=404)

        if not _can_access_detection_task(request.user, task):
            return Response({"message": "Detection task not found"}, status=404)

        if not task.resource_files.filter(id=file_management.id).exists():
            return Response({"message": "File does not belong to this task"}, status=404)

        task_text, task_text_source = _get_task_preview_text(task, file_management)
        if task_text:
            return _build_preview_response(
                file_management=file_management,
                text_content=task_text,
                source=task_text_source,
            )

    stored_path = (file_management.stored_path or "").strip()
    if not stored_path:
        return Response({"message": "File path is empty"}, status=400)

    file_path = stored_path if os.path.isabs(stored_path) else os.path.join(settings.MEDIA_ROOT, stored_path)
    if not os.path.exists(file_path):
        return Response({"message": "File path does not exist"}, status=404)

    processed = preprocess_document(file_path)
    text_content = processed.get("text_content") or ""

    return _build_preview_response(
        file_management=file_management,
        text_content=text_content,
        source="file_extraction",
        paragraphs=processed.get("paragraphs") or [],
        segments=processed.get("segments") or [],
        references=processed.get("references") or [],
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_file_tag(request, file_id):
    try:
        file_record = FileManagement.objects.get(id=file_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found."}, status=404)

    tag = request.data.get("tag")
    if tag not in [choice[0] for choice in FileManagement.TAG_CHOICES]:
        return Response({"message": "Invalid tag type."}, status=400)

    file_record.tag = tag
    file_record.save()

    return Response({
        "message": "File add tag successfully",
        "file_id": file_record.id,
        "file_url": f"/media/{file_record.file_name}",
    })


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_all_file_images(request, file_management_id):
    try:
        file_management = FileManagement.objects.get(id=file_management_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    page = int(request.query_params.get("page", 1))
    page_size = min(int(request.query_params.get("page_size", 10)), 100)
    is_detect = request.query_params.get("isDetect")
    is_review = request.query_params.get("isReview")
    is_fake = request.query_params.get("isFake")

    images = ImageUpload.objects.filter(file_management=file_management)

    if is_detect in ["true", "True", "1"]:
        images = images.filter(isDetect=True)
    elif is_detect in ["false", "False", "0"]:
        images = images.filter(isDetect=False)

    if is_review in ["true", "True", "1"]:
        images = images.filter(isReview=True)
    elif is_review in ["false", "False", "0"]:
        images = images.filter(isReview=False)

    if is_fake in ["true", "True", "1"]:
        images = images.filter(isFake=True)
    elif is_fake in ["false", "False", "0"]:
        images = images.filter(isFake=False)

    paginator = Paginator(images, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response({"error": "Page not found"}, status=404)

    return Response({
        "file_id": file_management_id,
        "imgs": [
            {
                "img_id": image.id,
                "img_url": image.image.url,
                "isDetect": image.isDetect,
                "isReview": image.isReview,
                "isFake": image.isFake,
            }
            for image in page_obj.object_list
        ],
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total_count": paginator.count,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    })
