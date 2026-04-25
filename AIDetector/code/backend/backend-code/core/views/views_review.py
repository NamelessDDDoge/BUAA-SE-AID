from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.paginator import Paginator
from rest_framework import status
from django.db.models import Q

from ..models import ReviewRequest, ManualReview, DetectionResult, User, DetectionTask, PublisherReviewerRelationship, \
    ManualReview, ImageReview
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import (
    ReviewRequest,
    DetectionTask,
    ImageUpload,
    User,
    Log,
    ResourceReviewRequest,
    ResourceManualReview,
    FileManagement,
)
from core.util import send_notification
from core.models import Notification
import uuid


def _serialize_review_resource_file(file):
    return {
        'file_id': file.id,
        'id': file.id,
        'file_name': file.file_name,
        'resource_type': file.resource_type,
        'file_size': file.file_size,
        'file_type': file.file_type,
        'file_url': file.stored_path if file.stored_path.startswith('/') else f"/media/{file.stored_path}" if file.stored_path else None,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_reviewers_in_org(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view all reviewers'}, status=403)

    # 获取查询参数
    query = request.query_params.get('query', '')

    # 构建查询条件
    reviewers = User.objects.filter(
        organization=user.organization,
        role='reviewer'
    )
    if query:
        reviewers = reviewers.filter(username__startswith=query)

    # 筛选具有审核权限的 reviewer
    filtered_reviewers = []
    for reviewer in reviewers:
        if reviewer.has_permission('review'):
            filtered_reviewers.append({
                'id': reviewer.id,
                'username': reviewer.username,
                'avatar': reviewer.avatar.url if reviewer.avatar else None,
            })

    return Response(filtered_reviewers)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reviewers_for_publisher(request, publisher_id):
    """获取指定Publisher所在组织下的所有reviewer"""
    try:
        publisher = User.objects.get(id=publisher_id, role='publisher')
    except User.DoesNotExist:
        return Response({'error': 'Publisher not found'}, status=404)

    # 获取该 publisher 所属组织
    organization = publisher.organization
    if not organization:
        return Response({'error': 'Publisher does not belong to any organization'}, status=400)

    # 获取该组织下所有 role 为 reviewer 的用户，并且有 review 权限
    reviewers = User.objects.filter(
        organization=organization,
        role='reviewer',
        is_active=True
    )

    # 序列化数据返回
    reviewer_list = [{
        'id': user.id,
        'username': user.username,
        'avatar': user.avatar.url if user.avatar else None,
    } for user in reviewers]

    return Response({
        'publisher_id': publisher_id,
        'reviewers': reviewer_list
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review_task_with_admin_check(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if not user.has_permission('publish'):
        return Response({"错误": "该用户没有发布的权限"}, status=403)

    if user.role != 'publisher':
        return Response({'error': 'Only publishers can create review tasks'}, status=403)

    image_ids = request.data.get('image_ids', [])
    reviewers = request.data.get('reviewers', [])
    reason = (request.data.get('reason', '') or '').strip()

    # 验证参数
    if not image_ids:
        return Response({'error': 'image_ids is required'}, status=400)
    if not reviewers:
        return Response({'error': 'reviewers is required'}, status=400)
    if not reason:
        return Response({'error': 'reason is required'}, status=400)

    try:
        # 获取图片对象
        images = ImageUpload.objects.filter(id__in=image_ids)
        if len(images) != len(image_ids):
            return Response({'error': 'Some image IDs do not exist'}, status=404)

        # 获取审核员对象
        reviewer_users = User.objects.filter(organization=user.organization, id__in=reviewers, role='reviewer')
        if len(reviewer_users) != len(reviewers):
            return Response({'error': 'Some reviewer IDs do not exist or are not reviewers'}, status=404)

        detection_result = images[0].detection_results.first()
        if not detection_result:
            return Response({'error': 'No detection result found for the provided images'}, status=404)

        # 创建审核请求，状态设为pending
        review_request = ReviewRequest.objects.create(
            detection_result=detection_result,
            user=request.user,
            reason=reason,
            organization=user.organization,
        )

        review_request.imgs.add(*images)
        # 添加审核人员
        for reviewer in reviewer_users:
            review_request.reviewers.add(reviewer)

        # 通知管理员进行检查
        organization = user.organization
        if organization and organization.admin_user:
            admin_email = organization.admin_user.email
        else:
            return Response({'error': 'Organization or admin user not found'}, status=404)

        send_mail(
            '新的审核任务',
            '您有一个新的审核任务需要审核，请登录系统进行处理。',
            '2406854677@qq.com',
            [admin_email],
            fail_silently=False,
        )

        # 创建日志
        # 在Log表中记录上传操作
        Log.objects.create(
            user=request.user,
            operation_type='review_request',
            related_model='ReviewRequest',
            related_id=review_request.id,
        )
        return Response(
            {'message': 'Review task created and sent to admin for approval', 'review_request_id': review_request.id},
            status=201
        )

    except ObjectDoesNotExist as e:
        return Response({'error': 'Resource not found'}, status=404)

    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_resource_review_task_placeholder(request):
    """
    论文 / Review 人工审核提交接口。
    """
    user = request.user
    if not user.has_permission('publish'):
        return Response({'error': '该用户没有发布人工审核的权限'}, status=403)

    if user.role != 'publisher':
        return Response({'error': 'Only publishers can create review tasks'}, status=403)

    task_id = request.data.get('task_id')
    reviewers = request.data.get('reviewers', [])
    reason = (request.data.get('reason', '') or '').strip()
    selected_file_ids = request.data.get('selected_file_ids', [])

    if not task_id:
        return Response({'error': 'task_id is required'}, status=400)
    if not isinstance(reviewers, list) or not reviewers:
        return Response({'error': 'reviewers is required and must be a non-empty list'}, status=400)
    if not reason:
        return Response({'error': 'reason is required'}, status=400)
    if selected_file_ids and not isinstance(selected_file_ids, list):
        return Response({'error': 'selected_file_ids must be a list'}, status=400)

    try:
        detection_task = DetectionTask.objects.get(id=task_id, user=user)
    except DetectionTask.DoesNotExist:
        return Response({'error': 'Detection task not found or permission denied'}, status=404)

    if detection_task.task_type not in ('paper', 'review'):
        return Response({'error': 'This endpoint only supports paper/review tasks'}, status=400)
    if detection_task.status != 'completed':
        return Response({'error': 'Task is not completed yet'}, status=400)

    reviewer_users = User.objects.filter(
        organization=user.organization,
        id__in=reviewers,
        role='reviewer',
        is_active=True,
    )
    if reviewer_users.count() != len(set(reviewers)):
        return Response({'error': 'Some reviewer IDs do not exist or are not reviewers'}, status=404)

    if selected_file_ids:
        selected_files = detection_task.resource_files.filter(id__in=selected_file_ids)
        if selected_files.count() != len(set(selected_file_ids)):
            return Response({'error': 'Some selected_file_ids do not belong to current task'}, status=400)
    else:
        selected_files = detection_task.resource_files.all()

    review_request = ResourceReviewRequest.objects.create(
        detection_task=detection_task,
        task_type=detection_task.task_type,
        user=user,
        organization=user.organization,
        reason=reason,
    )
    review_request.reviewers.add(*reviewer_users)
    review_request.selected_files.add(*selected_files)

    organization = user.organization
    if organization and organization.admin_user and organization.admin_user.email:
        send_mail(
            '新的资源人工审核任务',
            '您有新的论文/Review人工审核任务需要审批，请登录系统处理。',
            '2406854677@qq.com',
            [organization.admin_user.email],
            fail_silently=True,
        )

    Log.objects.create(
        user=user,
        operation_type='review_request',
        related_model='ResourceReviewRequest',
        related_id=review_request.id,
    )

    return Response({
        'message': 'Resource review request submitted',
        'review_request_id': review_request.id,
        'request_type': 'resource',
        'task_type': detection_task.task_type,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_img_review_all(request):
    """
    用于publisher获取指定ReviewRequest的可指定图片的**整体**审核结果
    """
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view task details'}, status=403)

    review_request_id = request.query_params.get('review_request_id', '')
    img_id = request.query_params.get('img_id', '')

    if not review_request_id:
        return Response({'error': 'review_request_id is required'}, status=400)
    if not img_id:
        return Response({'error': 'img_id is required'}, status=400)

    try:
        # 获取ReviewRequest对象
        review_request = ReviewRequest.objects.get(id=review_request_id)
    except ReviewRequest.DoesNotExist:
        return Response({'error': 'ReviewRequest not found'}, status=404)

    # 获取所有状态为completed的ManualReview对象
    manual_reviews = ManualReview.objects.filter(
        review_request=review_request,
        status='completed',
        imgs__id=img_id
    ).distinct()

    reviewers_results = []

    for manual_review in manual_reviews:
        reviewer = manual_review.reviewer
        # 获取相关的ImageReview对象
        image_reviews = ImageReview.objects.filter(
            manual_review=manual_review,
            img_id=img_id
        )

        for image_review in image_reviews:
            reviewers_results.append({
                'id': reviewer.id,
                'username': reviewer.username,
                'avatar': reviewer.avatar.url if reviewer.avatar else None,
                'result': image_review.result  # 0/1 表示人工审核的结果是真还是假
            })

    return Response({
        'reviewers_results': reviewers_results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_image_review(request):
    """
    用于publisher获取指定ReviewRequest的可指定图片的**单个详细**审核结果
    """
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view task details'}, status=403)

    review_request_id = request.query_params.get('review_request_id', '')
    img_id = request.query_params.get('img_id', '')
    reviewer_id = request.query_params.get('reviewer_id', '')

    if not review_request_id:
        return Response({'error': 'review_request_id is required'}, status=400)
    if not img_id:
        return Response({'error': 'img_id is required'}, status=400)
    if not reviewer_id:
        return Response({'error': 'reviewer_id is required'}, status=400)

    try:
        # 获取ReviewRequest对象
        review_request = ReviewRequest.objects.get(id=review_request_id)
    except ReviewRequest.DoesNotExist:
        return Response({'error': 'ReviewRequest not found'}, status=404)

    try:
        # 获取ManualReview对象
        manual_review = ManualReview.objects.get(
            review_request=review_request,
            reviewer_id=reviewer_id,
            imgs__id=img_id
        )
    except ManualReview.DoesNotExist:
        return Response({'error': 'ManualReview not found'}, status=404)

    try:
        # 获取ImageReview对象
        image_review = ImageReview.objects.get(
            manual_review=manual_review,
            img_id=img_id
        )
    except ImageReview.DoesNotExist:
        return Response({'error': 'ImageReview not found'}, status=404)

    scores = [
        image_review.score1,
        image_review.score2,
        image_review.score3,
        image_review.score4,
        image_review.score5,
        image_review.score6,
        image_review.score7
    ]

    reasons = [
        image_review.reason1,
        image_review.reason2,
        image_review.reason3,
        image_review.reason4,
        image_review.reason5,
        image_review.reason6,
        image_review.reason7
    ]

    points = [
        image_review.points1,
        image_review.points2,
        image_review.points3,
        image_review.points4,
        image_review.points5,
        image_review.points6,
        image_review.points7
    ]

    result = image_review.result

    return Response({
        'scores': scores,
        'reasons': reasons,
        'points': points,
        'result': result
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_request_completion_status(request, task_id):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view task completion status'}, status=403)

    try:
        detection_task = DetectionTask.objects.get(id=task_id)
    except DetectionTask.DoesNotExist:
        return Response({'error': 'Task not found'}, status=404)

    review_requests = detection_task.detection_results.first().review_requests.all()
    total_reviewers = review_requests.count()
    completed_reviewers = review_requests.filter(status='completed').count()

    completion_percentage = (completed_reviewers / total_reviewers) * 100 if total_reviewers > 0 else 0

    return Response({
        'task_id': task_id,
        'completion_percentage': completion_percentage
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_request_detail(request, reviewRequest_id):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view task details'}, status=403)

    request_type = request.query_params.get('request_type', 'image')

    if request_type == 'resource':
        try:
            resource_request = ResourceReviewRequest.objects.get(id=reviewRequest_id, user=user)
        except ResourceReviewRequest.DoesNotExist:
            return Response({'error': 'ResourceReviewRequest not found'}, status=404)

        manual_reviews = resource_request.manual_reviews.all()
        total_reviewers = resource_request.reviewers.count()
        completed_reviews_count = manual_reviews.filter(status='completed').count()
        status_payload = {
            'done': completed_reviews_count,
            'process': total_reviewers - completed_reviews_count,
        }
        selected_files = [
            _serialize_review_resource_file(file)
            for file in resource_request.selected_files.all()
        ]

        return Response({
            'request_type': 'resource',
            'task_type': resource_request.task_type,
            'task_id': resource_request.detection_task_id,
            'selected_files': selected_files,
            'status': status_payload,
            'reason': resource_request.reason,
            'ai_detection_result': {
                'result_summary': resource_request.detection_task.text_detection_results,
                'detection_time': resource_request.detection_task.completion_time.strftime('%Y-%m-%d %H:%M:%S')
                if resource_request.detection_task.completion_time else None,
            },
        })

    try:
        # 获取ReviewRequest对象
        review_request = ReviewRequest.objects.get(id=reviewRequest_id)
    except ReviewRequest.DoesNotExist:
        return Response({'error': 'ReviewRequest not found'}, status=404)

    # 获取关联的DetectionResult对象
    detection_result = review_request.detection_result
    if not detection_result:
        return Response({'error': 'No detection result found for the review request'}, status=404)

    # 获取关联的DetectionTask对象
    detection_task = detection_result.detection_task
    if not detection_task:
        return Response({'error': 'No detection task found for the review request'}, status=404)

    # 获取图片ID列表和URL列表
    images = []

    for img in review_request.imgs.all():
        images.append({
            'img_id': img.id,
            'img_url': img.image.url,
        })

    # 获取AI检测结果
    ai_detection_result = {
        'is_fake': detection_result.is_fake,
        'confidence_score': detection_result.confidence_score,
        'detection_time': detection_result.detection_time.strftime('%Y-%m-%d %H:%M:%S')
        if detection_result.detection_time else None
    }

    # 获取审核员的检测结果
    manual_reviews = ManualReview.objects.filter(review_request=review_request)
    # reviewers_results = [
    #     {
    #         'reviewer_id': manual_review.reviewer.id,
    #         'score': manual_review.score,
    #     } for manual_review in manual_reviews
    # ]

    # 计算状态
    total_reviewers = review_request.reviewers.count()
    completed_reviews_count = manual_reviews.filter(status='completed').count()
    status = {
        'done': completed_reviews_count,
        'process': total_reviewers - completed_reviews_count
    }

    return Response({
        'request_type': 'image',
        'images': images,
        'ai_detection_result': ai_detection_result,
        'status': status,
        # 'reviewers_results': reviewers_results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_publisher_review_tasks(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'error': 'Only publishers can view their review tasks'}, status=403)

    # 获取查询参数
    task_status = request.query_params.get('status', '')
    start_time = request.query_params.get('startTime', None)
    end_time = request.query_params.get('endTime', None)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))

    merged_tasks = []

    image_requests = ReviewRequest.objects.filter(user=user).prefetch_related('reviewers', 'manual_reviews')
    if task_status:
        image_requests = image_requests.filter(Q(status1=task_status) | Q(status2=task_status))
    if start_time:
        image_requests = image_requests.filter(request_time__gte=start_time)
    if end_time:
        image_requests = image_requests.filter(request_time__lte=end_time)

    for review_request in image_requests:
        reviewers_count = review_request.reviewers.count()
        completed_reviews_count = review_request.manual_reviews.filter(status='completed').count()
        display_status = review_request.status1 if review_request.status2 == 'accepted' else review_request.status2
        merged_tasks.append({
            'review_request_id': review_request.id,
            'request_type': 'image',
            'task_type': 'image',
            'task_id': review_request.detection_result.detection_task_id if review_request.detection_result else None,
            'task_name': (
                review_request.detection_result.detection_task.task_name
                if review_request.detection_result and review_request.detection_result.detection_task
                else None
            ),
            'request_time': review_request.request_time,
            'status': display_status,
            'status1': review_request.status1,
            'status2': review_request.status2,
            'progress': f"{completed_reviews_count}/{reviewers_count}",
        })

    resource_requests = ResourceReviewRequest.objects.filter(user=user).select_related('detection_task').prefetch_related('reviewers', 'manual_reviews')
    if task_status:
        resource_requests = resource_requests.filter(Q(status1=task_status) | Q(status2=task_status))
    if start_time:
        resource_requests = resource_requests.filter(request_time__gte=start_time)
    if end_time:
        resource_requests = resource_requests.filter(request_time__lte=end_time)

    for review_request in resource_requests:
        reviewers_count = review_request.reviewers.count()
        completed_reviews_count = review_request.manual_reviews.filter(status='completed').count()
        display_status = review_request.status1 if review_request.status2 == 'accepted' else review_request.status2
        merged_tasks.append({
            'review_request_id': review_request.id,
            'request_type': 'resource',
            'task_type': review_request.task_type,
            'task_id': review_request.detection_task_id,
            'task_name': review_request.detection_task.task_name if review_request.detection_task else None,
            'request_time': review_request.request_time,
            'status': display_status,
            'status1': review_request.status1,
            'status2': review_request.status2,
            'progress': f"{completed_reviews_count}/{reviewers_count}",
        })

    merged_tasks.sort(key=lambda item: item['request_time'], reverse=True)
    paginator = Paginator(merged_tasks, page_size)
    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=status.HTTP_400_BAD_REQUEST)

    tasks = []
    for item in page_obj.object_list:
        tasks.append({
            **item,
            'request_time': item['request_time'].strftime('%Y-%m-%d %H:%M:%S'),
        })

    return Response({
        'tasks': tasks,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reviewer_request_detail(request, reviewRequest_id):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'reviewer':
        return Response({'error': 'Only reviewers can view task details'}, status=403)

    try:
        # 获取ReviewRequest对象
        review_request = ReviewRequest.objects.get(id=reviewRequest_id)
    except ReviewRequest.DoesNotExist:
        return Response({'error': 'ReviewRequest not found'}, status=404)

    # 获取关联的DetectionResult对象
    detection_result = review_request.detection_result
    if not detection_result:
        return Response({'error': 'No detection result found for the review request'}, status=404)

    # 获取关联的DetectionTask对象
    detection_task = detection_result.detection_task
    if not detection_task:
        return Response({'error': 'No detection task found for the review request'}, status=404)

    # 获取图片ID列表和URL列表
    image_uploads = review_request.imgs.all()
    image_ids = [img.id for img in image_uploads]
    image_urls = [img.image.url for img in image_uploads]

    # 获取AI检测结果
    ai_detection_result = {
        'is_fake': detection_result.is_fake,
        'confidence_score': detection_result.confidence_score,
        'detection_time': detection_result.detection_time.strftime('%Y-%m-%d %H:%M:%S')
    }

    return Response({
        'image_ids': image_ids,
        'image_urls': image_urls,
        'ai_detection_result': ai_detection_result,
        'status': review_request.status1,
        'status2': review_request.status2,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reviewer_manual_request(request):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'reviewer':
        return Response({'error': 'Only reviewers can view tasks'}, status=403)

    # 获取查询参数
    task_status = request.query_params.get('status', '')
    query = request.query_params.get('query', '')
    start_time = request.query_params.get('start_time', None)
    end_time = request.query_params.get('end_time', None)
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))

    # 确保 page_size 不超过 100
    if page_size > 100:
        page_size = 100

    merged_results = []

    image_requests = ReviewRequest.objects.filter(reviewers=user).select_related('user')
    if query:
        image_requests = image_requests.filter(user__username__startswith=query)
    if start_time:
        image_requests = image_requests.filter(request_time__gte=start_time)
    if end_time:
        image_requests = image_requests.filter(request_time__lte=end_time)

    for review_request in image_requests:
        manual_review = review_request.manual_reviews.filter(reviewer=user).first()
        if not manual_review:
            continue
        if task_status and manual_review.status != task_status:
            continue
        merged_results.append({
            'manual_review_id': manual_review.id,
            'request_type': 'image',
            'task_type': 'image',
            'manual_review_time': manual_review.review_time,
            'publisher_username': review_request.user.username,
            'publisher_avatar': review_request.user.avatar.url if review_request.user.avatar else None,
            'item_count': review_request.imgs.count(),
            'status': manual_review.status,
        })

    resource_requests = ResourceReviewRequest.objects.filter(reviewers=user).select_related('user', 'detection_task')
    if query:
        resource_requests = resource_requests.filter(user__username__startswith=query)
    if start_time:
        resource_requests = resource_requests.filter(request_time__gte=start_time)
    if end_time:
        resource_requests = resource_requests.filter(request_time__lte=end_time)

    for review_request in resource_requests:
        manual_review = review_request.manual_reviews.filter(reviewer=user).first()
        if not manual_review:
            continue
        if task_status and manual_review.status != task_status:
            continue
        merged_results.append({
            'manual_review_id': manual_review.id,
            'request_type': 'resource',
            'task_type': review_request.task_type,
            'manual_review_time': manual_review.review_time,
            'publisher_username': review_request.user.username,
            'publisher_avatar': review_request.user.avatar.url if review_request.user.avatar else None,
            'item_count': review_request.selected_files.count(),
            'status': manual_review.status,
        })

    merged_results.sort(key=lambda item: item['manual_review_time'], reverse=True)

    paginator = Paginator(merged_results, page_size)
    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=400)

    results = []
    for item in page_obj.object_list:
        results.append({
            'manual_review_id': item['manual_review_id'],
            'request_type': item['request_type'],
            'task_type': item['task_type'],
            'manual_review_time': item['manual_review_time'].strftime('%Y-%m-%d %H:%M:%S'),
            'publisher_username': item['publisher_username'],
            'publisher_avatar': item['publisher_avatar'],
            'image_count': item['item_count'],
            'status': item['status'],
        })

    return Response({
        'results': results,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_review_detail(request, manual_review_id):
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'reviewer':
        return Response({'error': 'Only reviewers can view review details'}, status=403)

    request_type = request.query_params.get('request_type', 'image')

    if request_type == 'resource':
        try:
            manual_review = ResourceManualReview.objects.select_related('review_request__detection_task').get(
                id=manual_review_id,
                reviewer=user,
            )
        except ResourceManualReview.DoesNotExist:
            return Response({'error': 'ResourceManualReview not found'}, status=404)

        review_request = manual_review.review_request
        task = review_request.detection_task
        selected_files = [
            _serialize_review_resource_file(file)
            for file in review_request.selected_files.all()
        ]

        return Response({
            'request_type': 'resource',
            'task_type': review_request.task_type,
            'task_id': task.id,
            'task_name': task.task_name,
            'status': manual_review.status,
            'selected_files': selected_files,
            'reason': review_request.reason,
            'detection_result_summary': task.text_detection_results,
            'result_payload': manual_review.result_payload or {},
            'conclusion': manual_review.conclusion,
        })

    try:
        # 获取ManualReview对象
        manual_review = ManualReview.objects.get(id=manual_review_id, reviewer=user)
    except ManualReview.DoesNotExist:
        return Response({'error': 'ManualReview not found'}, status=404)

    # 获取关联的ReviewRequest对象
    review_request = manual_review.review_request

    # 获取关联的DetectionResult对象
    detection_result = review_request.detection_result

    # 获取关联的DetectionTask对象
    detection_task = detection_result.detection_task

    # 获取图片ID列表
    image_ids = [image_upload.id for image_upload in manual_review.imgs.all()]

    # 获取图片URL列表
    image_urls = [image_upload.image.url for image_upload in manual_review.imgs.all()]

    # 获取AI检测结果
    ai_detection_result = {
        'is_fake': detection_result.is_fake,
        'confidence_score': detection_result.confidence_score,
        'detection_time': detection_result.detection_time.strftime('%Y-%m-%d %H:%M:%S')
    }

    # 获取审核员的检测结果
    reviewers_results = []
    for image_review in manual_review.img_reviews.all():
        scores = [
            image_review.score1,
            image_review.score2,
            image_review.score3,
            image_review.score4,
            image_review.score5,
            image_review.score6,
            image_review.score7
        ]

        reasons = [
            image_review.reason1,
            image_review.reason2,
            image_review.reason3,
            image_review.reason4,
            image_review.reason5,
            image_review.reason6,
            image_review.reason7
        ]

        result = image_review.result

        reviewers_results.append({
            'image_id': image_review.img.id,
            'scores': scores,
            'reasons': reasons,
            'result': result
        })

    return Response({
        'request_type': 'image',
        'image_urls': image_urls,
        'ai_detection_result': ai_detection_result,
        'count': len(image_ids),
        'reviewers_results': reviewers_results
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manualReview_from_reviewRequestId(request, review_request_id):
    user = request.user

    try:
        # 获取对应的 ReviewRequest
        review_request = ReviewRequest.objects.get(id=review_request_id)
    except ReviewRequest.DoesNotExist:
        return Response({'error': 'ReviewRequest not found'}, status=status.HTTP_404_NOT_FOUND)

    # 获取所有关联的 ManualReview
    manual_reviews = ManualReview.objects.filter(review_request=review_request).select_related('reviewer')

    if not manual_reviews.exists():
        return Response({'message': 'No manual reviews found for this request'}, status=status.HTTP_404_NOT_FOUND)

    # 构造响应数据
    data = []
    for manual_review in manual_reviews:
        reviewers_results = []

        # 获取该 ManualReview 对应的 ImageReview 数据
        image_reviews = manual_review.image_reviews.all()
        for image_review in image_reviews:
            reviewers_results.append({
                'img_id': image_review.img.id,
                'result': image_review.result,
                'review_time': image_review.review_time.strftime(
                    '%Y-%m-%d %H:%M:%S') if image_review.review_time else None
            })

        data.append({
            'manual_review_id': manual_review.id,
            'review_request_id': manual_review.review_request.id,
            'reviewer': {
                'id': manual_review.reviewer.id,
                'username': manual_review.reviewer.username,
                'avatar': manual_review.reviewer.avatar.url if manual_review.reviewer.avatar else None,
            },
            'status': manual_review.status,
            'review_time': manual_review.review_time.strftime(
                '%Y-%m-%d %H:%M:%S') if manual_review.review_time else None,
            'image_reviews': reviewers_results,
            'report_file': manual_review.report_file.url if manual_review.report_file else None
        })

    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_review(request, manual_review_id):
    """
    reviewer提交审核结果
    """
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if not user.has_permission('review'):
        return Response({"错误": "该用户没有审核的权限"}, status=403)
    if user.role != 'reviewer':
        return Response({'error': 'Only reviewers can submit reviews'}, status=403)

    request_type = request.data.get('request_type', request.query_params.get('request_type', 'image'))

    if request_type == 'resource':
        try:
            manual_review = ResourceManualReview.objects.select_related('review_request').get(
                id=manual_review_id,
                reviewer=user,
            )
        except ResourceManualReview.DoesNotExist:
            return Response({'error': 'ResourceManualReview not found'}, status=404)

        payload = request.data.get('payload')
        if payload is None:
            payload = {
                'final_decision': request.data.get('final_decision'),
                'comment': request.data.get('comment', ''),
                'steps': request.data.get('steps', []),
            }
        if not isinstance(payload, dict):
            return Response({'error': 'payload must be an object'}, status=400)

        manual_review.result_payload = payload
        manual_review.conclusion = str(payload.get('comment') or request.data.get('comment') or '')
        manual_review.status = 'completed'
        manual_review.review_time = timezone.now()
        manual_review.save(update_fields=['result_payload', 'conclusion', 'status', 'review_time'])

        review_request = manual_review.review_request
        total_count = review_request.reviewers.count()
        completed_count = review_request.manual_reviews.filter(status='completed').count()
        if completed_count == total_count:
            review_request.status1 = 'completed'
            review_request.review_end_time = timezone.now()
        else:
            review_request.status1 = 'in_progress'
        review_request.save(update_fields=['status1', 'review_end_time'])

        Log.objects.create(
            user=request.user,
            operation_type='manual_review',
            related_model='ResourceManualReview',
            related_id=manual_review_id,
        )

        send_notification(
            receiver_id=review_request.user.id,
            receiver_name=review_request.user.username,
            sender_id=user.id,
            sender_name=user.username,
            category=Notification.R2P,
            title='资源人工审核完成通知',
            content=f'审稿人 {user.username} 已完成{review_request.task_type}任务人工审核',
            url=f'/task/{review_request.id}?request_type=resource'
        )
        return Response({'message': 'Resource review submitted successfully'}, status=201)

    try:
        # 获取ManualReview对象
        manual_review = ManualReview.objects.get(id=manual_review_id, reviewer=user)
    except ManualReview.DoesNotExist:
        return Response({'error': 'ManualReview not found'}, status=404)

    # 获取请求体数据
    data = request.data
    results = data.get('result', [])

    if not results:
        return Response({'error': 'result is required'}, status=400)

    for item in results:
        img_id = item.get('img_id')
        scores = item.get('score', [])
        reasons = item.get('reason', [])
        points_list = item.get('points', [])  # 获取 points 列表
        final_result = item.get('final')

        if not img_id:
            return Response({'error': 'img_id is required in each result item'}, status=400)
        if len(scores) != 7:
            return Response({'error': 'scores must contain exactly 7 elements'}, status=400)
        if len(reasons) != 7:
            return Response({'error': 'reasons must contain exactly 7 elements'}, status=400)
        if len(points_list) != 7:
            return Response({'error': 'points must contain exactly 7 elements (one for each method)'}, status=400)
        if final_result is None:
            return Response({'error': 'final is required in each result item'}, status=400)

        try:
            image_upload = ImageUpload.objects.get(id=img_id)
        except ImageUpload.DoesNotExist:
            return Response({'error': f'Image with ID {img_id} not found'}, status=404)

        # 创建或更新 ImageReview 对象
        image_review, created = ImageReview.objects.update_or_create(
            manual_review=manual_review,
            img=image_upload,
            defaults={
                'score1': scores[0],
                'score2': scores[1],
                'score3': scores[2],
                'score4': scores[3],
                'score5': scores[4],
                'score6': scores[5],
                'score7': scores[6],
                'reason1': reasons[0],
                'reason2': reasons[1],
                'reason3': reasons[2],
                'reason4': reasons[3],
                'reason5': reasons[4],
                'reason6': reasons[5],
                'reason7': reasons[6],
                'points1': points_list[0],  # 存储第一个方法的坐标点
                'points2': points_list[1],  # 第二个方法
                'points3': points_list[2],
                'points4': points_list[3],
                'points5': points_list[4],
                'points6': points_list[5],
                'points7': points_list[6],
                'result': final_result,
                'review_time': timezone.now()
            }
        )

        # 更新 image_upload 的 isReview 字段
        image_upload.isReview = True
        image_upload.save(update_fields=['isReview'])

    # 更新ManualReview状态
    manual_review.status = 'completed'
    manual_review.save()

    # 更新ReviewRequest状态
    review_request = manual_review.review_request
    if review_request.manual_reviews.filter(status='completed').count() == review_request.reviewers.count():
        review_request.status1 = 'completed'
        review_request.review_end_time = timezone.now()
    else:
        review_request.status1 = 'in_progress'
    review_request.save()

    # 在Log表中记录上传操作
    Log.objects.create(
        user=request.user,
        operation_type='manual_review',
        related_model='ManualReview',
        related_id=manual_review_id
    )

    # wyt shit here
    send_notification(
        receiver_id=review_request.user.id,
        receiver_name=review_request.user.username,
        sender_id=user.id,
        sender_name=user.username,
        category=Notification.R2P,
        title='任务完成通知',
        content=f'审稿人 {user.username} 已完成人工审核任务',
        url=f'/task/{review_request.id}'
    )

    return Response({'message': 'Review submitted successfully'}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def if_publisher_can_access_dectection_task(request):
    """
    只有这个detection_task是由这个publisher发布的，才可以访问
    """
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'publisher':
        return Response({'access': False})
    task_id = request.query_params.get('task_id')
    if not task_id:
        return Response({'error': 'task_id is required'}, status=400)
    task = DetectionTask.objects.filter(id=task_id, user=user).first()
    if task:
        return Response({'access': True, 'task_type': task.task_type})
    return Response({'access': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def if_reviewer_can_access_manual_review(request):
    """
    只有这个manual_review是由这个reviewer提交的，才可以访问
    """
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    if user.role != 'reviewer':
        return Response({'access': False})
    manual_review_id = request.query_params.get('manual_review_id')
    if not manual_review_id:
        return Response({'error': 'manual_review_id is required'}, status=400)
    access = ManualReview.objects.filter(id=manual_review_id, reviewer=user).exists()
    return Response({'access': access})
