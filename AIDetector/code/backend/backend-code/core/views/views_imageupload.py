import io
import os
import uuid
from PIL import Image
import zipfile
from django.core.files.storage import FileSystemStorage
from ..models import FileManagement, ImageUpload, Log, User
from django.core.paginator import Paginator, EmptyPage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from ..models import ImageUpload


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if not user.has_permission('upload'):
        return Response({"错误": "该用户没有上传文件的权限"}, status=403)

    detection_type = request.data.get('detection_type', 'image')
    review_role = request.data.get('review_role', '')
    linked_paper_file_id = request.data.get('linked_paper_file_id')

    valid_detection_types = {'image', 'paper', 'review'}
    if detection_type not in valid_detection_types:
        return Response({'message': 'Invalid detection_type'}, status=400)

    # 获取上传的文件
    uploaded_file = request.FILES.get('file')
    if uploaded_file is None:
        return Response({'message': 'file is required'}, status=400)

    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    max_size = 100 * 1024 * 1024
    if uploaded_file.size > max_size:
        return Response({'message': 'File size exceeds 100MB limit'}, status=400)

    allowed_image_ext = {'.png', '.jpg', '.jpeg', '.zip'}
    allowed_paper_ext = {'.docx', '.pdf', '.zip'}
    allowed_review_ext = {'.docx', '.pdf', '.txt', '.zip'}

    linked_paper_file = None
    if detection_type == 'image':
        if file_ext not in allowed_image_ext:
            return Response({'message': 'Unsupported image file format'}, status=400)
    elif detection_type == 'paper':
        if file_ext not in allowed_paper_ext:
            return Response({'message': 'Unsupported paper file format'}, status=400)
    else:
        if review_role not in {'paper', 'review'}:
            return Response({'message': 'review_role must be paper or review'}, status=400)

        if review_role == 'paper':
            if file_ext not in allowed_paper_ext:
                return Response({'message': 'Unsupported review-paper file format'}, status=400)
        else:
            if file_ext not in allowed_review_ext:
                return Response({'message': 'Unsupported review file format'}, status=400)
            if not linked_paper_file_id:
                return Response({'message': 'Review upload must include linked_paper_file_id'}, status=400)

            try:
                linked_paper_file = FileManagement.objects.get(id=linked_paper_file_id, user=request.user)
            except FileManagement.DoesNotExist:
                return Response({'message': 'Linked paper file not found'}, status=404)

            if linked_paper_file.resource_type != 'review_paper':
                return Response({'message': 'linked_paper_file_id is not a review paper file'}, status=400)

    if detection_type == 'image':
        resource_type = 'image'
    elif detection_type == 'paper':
        resource_type = 'paper'
    elif review_role == 'paper':
        resource_type = 'review_paper'
    else:
        resource_type = 'review_file'

    file_name = uploaded_file.name
    file_size = uploaded_file.size
    file_type = uploaded_file.content_type or 'application/octet-stream'

    # 存储文件到 FileManagement 表
    file_management = FileManagement.objects.create(
        organization=user.organization,
        user=request.user,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type,
        resource_type=resource_type,
        linked_file=linked_paper_file
    )

    # 使用 FileSystemStorage 保存上传文件，路径基于 MEDIA_ROOT 下的 uploads 目录
    unique_filename = f"{uuid.uuid4().hex}_{file_name}"
    fs = FileSystemStorage()
    file_path = fs.save(f'uploads/{unique_filename}', uploaded_file)
    file_url = fs.url(file_path)
    file_management.stored_path = file_path
    file_management.save(update_fields=['stored_path'])

    # 仅图像检测任务提取图片
    if detection_type == 'image':
        if file_ext == '.pdf':
            extract_images_from_pdf(file_management, file_path)
        elif file_ext == '.zip':
            extract_images_from_zip(file_management, uploaded_file)
        else:
            store_image(file_management, uploaded_file)

    # 在Log表中记录上传操作
    Log.objects.create(
        user=request.user,
        operation_type='upload',
        related_model='FileManagement',
        related_id=file_management.id
    )

    return Response({
        "message": "File uploaded successfully",
        "file_id": file_management.id,
        "file_url": file_url,
        "detection_type": detection_type,
        "resource_type": resource_type,
        "linked_paper_file_id": linked_paper_file.id if linked_paper_file else None
    })


import threading
from django.conf import settings

# 全局锁（可选，根据并发需求）
# fitz_lock = threading.Lock()


def extract_images_from_pdf(file_management, file_path):
    import fitz
    full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)

    # 使用锁确保线程安全（根据实际情况选择是否添加）
    # with fitz_lock:
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
                    image_filename = f"{file_management.id}_page{page_number + 1}_image{image_index + 1}.{image_ext}"

                    # 保存图像
                    relative_image_path = save_image_pdf(image_bytes, image_filename)

                    # 创建数据库记录
                    ImageUpload.objects.create(
                        file_management=file_management,
                        image=relative_image_path,
                        extracted_from_pdf=True,
                        page_number=page_number + 1,
                        isDetect=False,
                        isReview=False,
                        isFake=False
                    )
            finally:
                del page  # 帮助GC及时回收
    return


def extract_images_from_zip(file_management, uploaded_file):
    with zipfile.ZipFile(uploaded_file) as zip_file:
        for file_name in zip_file.namelist():
            # 跳过目录
            file_info = zip_file.getinfo(file_name)
            if file_info.is_dir():
                continue

            # 处理图片文件（png/jpg/jpeg）
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img_data = zip_file.read(file_name)
                    image = Image.open(io.BytesIO(img_data))
                    image_name = f"{file_management.id}_{os.path.basename(file_name)}"
                    relative_image_path = save_image_zip(image, image_name)
                    ImageUpload.objects.create(
                        file_management=file_management,
                        image=relative_image_path,
                        extracted_from_pdf=False,
                        isDetect=False,
                        isReview=False,
                        isFake=False
                    )
                except Exception as e:
                    print(f"处理ZIP中的图片文件 {file_name} 时出错: {e}")

            # 处理PDF文件
            elif file_name.lower().endswith('.pdf'):
                temp_pdf_path = None
                try:
                    # 读取PDF内容
                    pdf_data = zip_file.read(file_name)
                    # 创建临时目录和文件名
                    temp_pdf_dir = os.path.join(settings.MEDIA_ROOT, 'temp_pdfs')
                    os.makedirs(temp_pdf_dir, exist_ok=True)
                    temp_pdf_filename = f"{uuid.uuid4().hex}.pdf"
                    temp_pdf_path = os.path.join(temp_pdf_dir, temp_pdf_filename)
                    # 保存到临时文件
                    with open(temp_pdf_path, 'wb') as f:
                        f.write(pdf_data)
                    # 构造相对路径
                    relative_temp_pdf_path = os.path.join('temp_pdfs', temp_pdf_filename)
                    # 调用PDF处理函数
                    extract_images_from_pdf(file_management, relative_temp_pdf_path)
                except Exception as e:
                    print(f"处理ZIP中的PDF文件 {file_name} 时出错: {e}")
                finally:
                    # 清理临时文件
                    if temp_pdf_path and os.path.exists(temp_pdf_path):
                        try:
                            os.remove(temp_pdf_path)
                        except Exception as e:
                            print(f"删除临时文件 {temp_pdf_path} 失败: {e}")


def save_image_pdf(image_data, image_name):
    # 构造相对路径（保存在 MEDIA_ROOT 下的 extracted_images 文件夹中）
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join('extracted_images', unique_image_name)
    relative_path = relative_path.replace('\\', '/')
    # 组合成完整路径
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    # 确保保存目录存在
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # 使用 PIL 打开并保存图像
    image = Image.open(io.BytesIO(image_data))
    image.save(full_path)

    # 返回相对路径，后续可以通过 settings.MEDIA_URL 进行访问
    return relative_path


def save_image_zip(image, image_name):
    # 构造相对路径，保存在 MEDIA_ROOT 下的 extracted_images 文件夹中
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join('extracted_images', unique_image_name)
    relative_path = relative_path.replace('\\', '/')
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    image.save(full_path)
    return relative_path


def store_image(file_management, uploaded_file):
    # 构造相对路径，将文件存储在 MEDIA_ROOT 下的 extracted_images 目录中
    unique_filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    relative_path = os.path.join('extracted_images', f"{file_management.id}_{unique_filename}")
    relative_path = relative_path.replace('\\', '/')
    fs = FileSystemStorage()
    fs.save(relative_path, uploaded_file)

    ImageUpload.objects.create(
        file_management=file_management,
        image=relative_path,
        extracted_from_pdf=False,
        isDetect=False,  # 初始值设为False
        isReview=False,  # 初始值设为False
        isFake=False  # 初始值设为False
    )


from django.utils import timezone


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_file_details(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
        extracted_images = ImageUpload.objects.filter(file_management=file_management)
        image_urls = [image.image.url for image in extracted_images]

        is_pdf = file_management.file_type == 'application/pdf'

        return Response({
            "file_id": file_management.id,
            "user_id": file_management.user.id,
            "file_name": file_management.file_name,
            "file_url": file_management.file_size,  # 可返回文件的URL
            "upload_time": timezone.localtime(file_management.upload_time),
            "is_pdf": is_pdf,
            "extracted_images": image_urls
        })
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)


from .views_dectection import CustomPagination


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_extracted_images(request, file_id):
    try:
        # 获取文件对象并验证权限
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
        if file_management.resource_type != 'image':
            return Response({
                "message": "Current file type has no extracted images",
                "file_id": file_management.id,
                "resource_type": file_management.resource_type
            }, status=400)

        # 按图片ID倒序排列（可根据需要改为其他字段如上传时间）
        extracted_images = ImageUpload.objects.filter(
            file_management=file_management
        ).order_by('-id')

        # 使用自定义分页类
        paginator = CustomPagination()
        paginated_images = paginator.paginate_queryset(extracted_images, request)

        # 构建图片列表
        image_list = []
        for image in paginated_images:
            image_data = {
                "image_id": image.id,
                "image_url": image.image.url,
                "page_number": image.page_number if image.extracted_from_pdf else None,
                "extracted_from_pdf": image.extracted_from_pdf,
                "isDetect": image.isDetect,
                "isReview": image.isReview,
                "isFake": image.isFake
            }
            image_list.append(image_data)

        # 构造包含分页信息的响应
        return Response({
            "file_id": file_management.id,
            "page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "total": paginator.page.paginator.count,
            "images": image_list
        })

    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_file_tag(request, file_id):
    try:
        file = FileManagement.objects.get(id=file_id)
        tag = request.data.get('tag')

        if tag not in [choice[0] for choice in FileManagement.TAG_CHOICES]:
            return Response({"message": "Invalid tag type."}, status=400)

        file.tag = tag
        file.save()

        return Response({
            "message": "File add tag successfully",
            "file_id": file.id,
            "file_url": f"/media/{file.file_name}"
        })

    except FileManagement.DoesNotExist:
        return Response({"message": "File not found."}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_all_file_images(request, file_management_id):
    """
    获取指定文件的所有图片信息，支持分页和筛选。
    """

    try:
        file_management = FileManagement.objects.get(id=file_management_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    # 获取查询参数
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    is_detect = request.query_params.get('isDetect')
    is_review = request.query_params.get('isReview')
    is_fake = request.query_params.get('isFake')

    # 确保 page_size 不超过最大限制
    if page_size > 100:
        page_size = 100

    # 构建查询集：只获取该 file_management 下的图片
    images = ImageUpload.objects.filter(file_management=file_management)

    # 应用筛选条件
    if is_detect in ['true', 'True', '1']:
        images = images.filter(isDetect=True)
    elif is_detect in ['false', 'False', '0']:
        images = images.filter(isDetect=False)

    if is_review in ['true', 'True', '1']:
        images = images.filter(isReview=True)
    elif is_review in ['false', 'False', '0']:
        images = images.filter(isReview=False)

    if is_fake in ['true', 'True', '1']:
        images = images.filter(isFake=True)
    elif is_fake in ['false', 'False', '0']:
        images = images.filter(isFake=False)

    # 分页处理
    paginator = Paginator(images, page_size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response({'error': 'Page not found'}, status=404)

    # 构造返回数据
    results = []
    for image in page_obj.object_list:
        results.append({
            "img_id": image.id,
            "img_url": image.image.url,
            "isDetect": image.isDetect,
            "isReview": image.isReview,
            "isFake": image.isFake,
        })

    return Response({
        "file_id": file_management_id,
        "imgs": results,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total_count": paginator.count,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous()
    })
