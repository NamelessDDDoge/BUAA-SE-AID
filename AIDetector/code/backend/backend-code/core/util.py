from django.utils import timezone
from .models import Notification, DetectionResult, ManualReview


def send_notification(receiver_id, receiver_name, sender_id=None, sender_name=None, category=None, title=None,
                      content=None, url=None):
    """
    发送通知
    :param receiver_id: 收件人ID
    :param receiver_name: 收件人名称
    :param sender_id: 发件人ID（可选）
    :param sender_name: 发件人名称（可选）
    :param category: 通知类型 (1:全局, 2:系统, 3:出版社给审稿人, 4:审稿人给出版社)
    :param title: 通知标题
    :param content: 通知内容
    """
    Notification.objects.create(
        receiver_id=receiver_id,
        receiver_name=receiver_name,
        sender_id=sender_id,
        sender_name=sender_name,
        category=category,
        title=title,
        content=content,
        status='unread',
        notified_at=timezone.now(),
        url=url
    )


def send_ai_detection_complete_notification(user_id, user_name, task):
    """发送AI检测完成通知"""
    send_notification(
        receiver_id=user_id,
        receiver_name=user_name,
        category=Notification.SYSTEM,
        title='AI检测已完成',
        content='AI检测已完成，请查看结果',
        url=f'/step/{task.id}'
    )
