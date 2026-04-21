from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from ..models import FileManagement, ImageUpload, User
from ..services import log_user_event
from ..services.resources import save_uploaded_resource
from .views_dectection import CustomPagination


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
