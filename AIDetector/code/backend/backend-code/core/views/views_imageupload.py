import io
import os
import uuid
from PIL import Image
import zipfile
from django.core.files.storage import FileSystemStorage
from ..models import FileManagement, ImageUpload, User
from django.core.paginator import Paginator, EmptyPage
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from ..models import ImageUpload
from ..services import log_user_event
from ..services.resources import save_uploaded_resource


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if not user.has_permission('upload'):
        return Response({"閿欒": "璇ョ敤鎴锋病鏈変笂浼犳枃浠剁殑鏉冮檺"}, status=403)

    detection_type = request.data.get('detection_type', 'image')
    review_role = request.data.get('review_role', '')
    linked_paper_file_id = request.data.get('linked_paper_file_id')
    uploaded_file = request.FILES.get('file')

    try:
        upload_result = save_uploaded_resource(
            user=user,
            uploaded_file=uploaded_file,
            detection_type=detection_type,
            review_role=review_role,
            linked_paper_file_id=linked_paper_file_id,
        )
    except ValueError as exc:
        return Response({'message': str(exc)}, status=400)
    except FileNotFoundError as exc:
        return Response({'message': str(exc)}, status=404)

    log_user_event(
        user=request.user,
        operation_type='upload',
        related_model='FileManagement',
        related_id=upload_result['file_id']
    )

    return Response({
        "message": "File uploaded successfully",
        **upload_result
    })


import threading
from django.conf import settings

# 鍏ㄥ眬閿侊紙鍙€夛紝鏍规嵁骞跺彂闇€姹傦級
# fitz_lock = threading.Lock()


def extract_images_from_pdf(file_management, file_path):
    import fitz
    full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)

    # 浣跨敤閿佺‘淇濈嚎绋嬪畨鍏紙鏍规嵁瀹為檯鎯呭喌閫夋嫨鏄惁娣诲姞锛?
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

                    # 淇濆瓨鍥惧儚
                    relative_image_path = save_image_pdf(image_bytes, image_filename)

                    # 鍒涘缓鏁版嵁搴撹褰?
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
                del page  # 甯姪GC鍙婃椂鍥炴敹
    return


def extract_images_from_zip(file_management, uploaded_file):
    with zipfile.ZipFile(uploaded_file) as zip_file:
        for file_name in zip_file.namelist():
            # 璺宠繃鐩綍
            file_info = zip_file.getinfo(file_name)
            if file_info.is_dir():
                continue

            # 澶勭悊鍥剧墖鏂囦欢锛坧ng/jpg/jpeg锛?
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
                    print(f"澶勭悊ZIP涓殑鍥剧墖鏂囦欢 {file_name} 鏃跺嚭閿? {e}")

            # 澶勭悊PDF鏂囦欢
            elif file_name.lower().endswith('.pdf'):
                temp_pdf_path = None
                try:
                    # 璇诲彇PDF鍐呭
                    pdf_data = zip_file.read(file_name)
                    # 鍒涘缓涓存椂鐩綍鍜屾枃浠跺悕
                    temp_pdf_dir = os.path.join(settings.MEDIA_ROOT, 'temp_pdfs')
                    os.makedirs(temp_pdf_dir, exist_ok=True)
                    temp_pdf_filename = f"{uuid.uuid4().hex}.pdf"
                    temp_pdf_path = os.path.join(temp_pdf_dir, temp_pdf_filename)
                    # 淇濆瓨鍒颁复鏃舵枃浠?
                    with open(temp_pdf_path, 'wb') as f:
                        f.write(pdf_data)
                    # 鏋勯€犵浉瀵硅矾寰?
                    relative_temp_pdf_path = os.path.join('temp_pdfs', temp_pdf_filename)
                    # 璋冪敤PDF澶勭悊鍑芥暟
                    extract_images_from_pdf(file_management, relative_temp_pdf_path)
                except Exception as e:
                    print(f"澶勭悊ZIP涓殑PDF鏂囦欢 {file_name} 鏃跺嚭閿? {e}")
                finally:
                    # 娓呯悊涓存椂鏂囦欢
                    if temp_pdf_path and os.path.exists(temp_pdf_path):
                        try:
                            os.remove(temp_pdf_path)
                        except Exception as e:
                            print(f"鍒犻櫎涓存椂鏂囦欢 {temp_pdf_path} 澶辫触: {e}")


def save_image_pdf(image_data, image_name):
    # 鏋勯€犵浉瀵硅矾寰勶紙淇濆瓨鍦?MEDIA_ROOT 涓嬬殑 extracted_images 鏂囦欢澶逛腑锛?
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join('extracted_images', unique_image_name)
    relative_path = relative_path.replace('\\', '/')
    # 缁勫悎鎴愬畬鏁磋矾寰?
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    # 纭繚淇濆瓨鐩綍瀛樺湪
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # 浣跨敤 PIL 鎵撳紑骞朵繚瀛樺浘鍍?
    image = Image.open(io.BytesIO(image_data))
    image.save(full_path)

    # 杩斿洖鐩稿璺緞锛屽悗缁彲浠ラ€氳繃 settings.MEDIA_URL 杩涜璁块棶
    return relative_path


def save_image_zip(image, image_name):
    # 鏋勯€犵浉瀵硅矾寰勶紝淇濆瓨鍦?MEDIA_ROOT 涓嬬殑 extracted_images 鏂囦欢澶逛腑
    unique_image_name = f"{uuid.uuid4().hex}_{image_name}"
    relative_path = os.path.join('extracted_images', unique_image_name)
    relative_path = relative_path.replace('\\', '/')
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    image.save(full_path)
    return relative_path


def store_image(file_management, uploaded_file):
    # 鏋勯€犵浉瀵硅矾寰勶紝灏嗘枃浠跺瓨鍌ㄥ湪 MEDIA_ROOT 涓嬬殑 extracted_images 鐩綍涓?
    unique_filename = f"{uuid.uuid4().hex}_{uploaded_file.name}"
    relative_path = os.path.join('extracted_images', f"{file_management.id}_{unique_filename}")
    relative_path = relative_path.replace('\\', '/')
    fs = FileSystemStorage()
    fs.save(relative_path, uploaded_file)

    ImageUpload.objects.create(
        file_management=file_management,
        image=relative_path,
        extracted_from_pdf=False,
        isDetect=False,  # 鍒濆鍊艰涓篎alse
        isReview=False,  # 鍒濆鍊艰涓篎alse
        isFake=False  # 鍒濆鍊艰涓篎alse
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
            "file_url": file_management.file_size,  # 鍙繑鍥炴枃浠剁殑URL
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
        # 鑾峰彇鏂囦欢瀵硅薄骞堕獙璇佹潈闄?
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
        if file_management.resource_type != 'image':
            return Response({
                "message": "Current file type has no extracted images",
                "file_id": file_management.id,
                "resource_type": file_management.resource_type
            }, status=400)

        # 鎸夊浘鐗嘔D鍊掑簭鎺掑垪锛堝彲鏍规嵁闇€瑕佹敼涓哄叾浠栧瓧娈靛涓婁紶鏃堕棿锛?
        extracted_images = ImageUpload.objects.filter(
            file_management=file_management
        ).order_by('-id')

        # 浣跨敤鑷畾涔夊垎椤电被
        paginator = CustomPagination()
        paginated_images = paginator.paginate_queryset(extracted_images, request)

        # 鏋勫缓鍥剧墖鍒楄〃
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

        # 鏋勯€犲寘鍚垎椤典俊鎭殑鍝嶅簲
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
    鑾峰彇鎸囧畾鏂囦欢鐨勬墍鏈夊浘鐗囦俊鎭紝鏀寔鍒嗛〉鍜岀瓫閫夈€?
    """

    try:
        file_management = FileManagement.objects.get(id=file_management_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    # 鑾峰彇鏌ヨ鍙傛暟
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    is_detect = request.query_params.get('isDetect')
    is_review = request.query_params.get('isReview')
    is_fake = request.query_params.get('isFake')

    # 纭繚 page_size 涓嶈秴杩囨渶澶ч檺鍒?
    if page_size > 100:
        page_size = 100

    # 鏋勫缓鏌ヨ闆嗭細鍙幏鍙栬 file_management 涓嬬殑鍥剧墖
    images = ImageUpload.objects.filter(file_management=file_management)

    # 搴旂敤绛涢€夋潯浠?
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

    # 鍒嗛〉澶勭悊
    paginator = Paginator(images, page_size)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response({'error': 'Page not found'}, status=404)

    # 鏋勯€犺繑鍥炴暟鎹?
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
