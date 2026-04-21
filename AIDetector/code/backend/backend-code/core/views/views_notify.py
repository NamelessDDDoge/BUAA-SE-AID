from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Notification, User
from rest_framework.response import Response
import json


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    try:
        user = request.user
        notifications = Notification.objects.filter(receiver_id=user.id)
        notifications_data = [{
            'id': n.id,
            'sender_id': n.sender_id,
            'sender_name': n.sender_name,
            'category': n.get_category_display(),
            'title': n.title,
            'content': n.content,
            'status': n.status,
            'notified_at': n.notified_at.strftime('%Y-%m-%d %H:%M:%S'),
            'url': n.url
        } for n in notifications]

        return Response({'notifications': notifications_data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_status(request):
    try:
        user = request.user
        unread_count = Notification.objects.filter(receiver_id=user.id, status='unread').count()
        return Response({
            'not_read': unread_count,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_notifications_as_read(request):
    try:
        user = request.user
        Notification.objects.filter(receiver_id=user.id, status='unread').update(status='read')
        return Response({'message': 'All notifications marked as read'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_single_notification_as_read(request, notification_id):
    try:
        user = request.user
        Notification.objects.filter(receiver_id=user.id, id=notification_id).update(status='read')
        return Response({'message': 'Notification marked as read'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def broadcast_notification(request):
    try:
        # 检查用户权限
        if not request.user.is_staff:
            return Response({'error': '只有管理员可以发送公告'}, status=403)

        title = request.data.get('title', '')
        content = request.data.get('content', '')

        # 验证参数
        if not title or not content:
            return Response({'error': '标题和内容不能为空'}, status=400)

        if len(title) > 15:
            return Response({'error': '标题长度不能超过15个字符'}, status=400)

        if len(content) > 1000:
            return Response({'error': '内容长度不能超过1000个字符'}, status=400)

        # 获取所有非管理员用户
        users = User.objects.filter(is_staff=False)

        # 为每个用户创建通知
        for user in users:
            Notification.objects.create(
                receiver_id=user.id,
                receiver_name=user.username,
                sender_id=request.user.id,
                sender_name=request.user.username,
                category=Notification.GLOBAL,
                title=title,
                content=content,
                status='unread',
                notified_at=timezone.now()
            )

        return Response({'message': '公告发送成功'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)
