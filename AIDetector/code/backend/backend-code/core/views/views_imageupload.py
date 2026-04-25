from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
import os

from ..models import FileManagement, ImageUpload, User
from ..services import log_user_event
from ..services.resources import save_uploaded_resource
from ..services.resources.document_preprocessor import preprocess_document
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

    if file_management.resource_type != "image":
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
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
    except FileManagement.DoesNotExist:
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

    stored_path = (file_management.stored_path or "").strip()
    if not stored_path:
        return Response({"message": "File path is empty"}, status=400)

    file_path = stored_path if os.path.isabs(stored_path) else os.path.join(settings.MEDIA_ROOT, stored_path)
    if not os.path.exists(file_path):
        return Response({"message": "File path does not exist"}, status=404)

    processed = preprocess_document(file_path)
    text_content = processed.get("text_content") or ""
    max_chars = 60000
    truncated = len(text_content) > max_chars
    preview_text = text_content[:max_chars]

    return Response(
        {
            "file_id": file_management.id,
            "file_name": file_management.file_name,
            "resource_type": file_management.resource_type,
            "text_content": preview_text,
            "text_truncated": truncated,
            "paragraph_count": len(processed.get("paragraphs") or []),
            "segment_count": len(processed.get("segments") or []),
            "reference_count": len(processed.get("references") or []),
            "paragraph_preview": (processed.get("paragraphs") or [])[:8],
            "reference_preview": (processed.get("references") or [])[:8],
        }
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
