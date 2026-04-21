from rest_framework import serializers, views
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from rest_framework import views, status
from ..models import ReviewRequest, ManualReview, DetectionTask, User, InvitationCode
from ..utils.report_generator import generate_manual_review_report


class EmailBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            user = get_user_model().objects.get(email=email)
            if user.check_password(password):
                return user
        except get_user_model().DoesNotExist:
            return None


class UserRegisterSerializer(serializers.ModelSerializer):
    invitation_code = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'organization', 'role', 'invitation_code']

    def validate_invitation_code(self, value):
        try:
            code_obj = InvitationCode.objects.get(code=value, is_used=False, expires_at__gt=timezone.now())
        except InvitationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invitation code.")
        return code_obj

    def create(self, validated_data):
        invitation_code = validated_data.pop('invitation_code')
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            organization=invitation_code.organization,
            role=invitation_code.role
        )
        # invitation_code.is_used = True
        invitation_code.save()
        return user



class UserRegisterView(views.APIView):
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User created successfully", "user_id": user.id},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import serializers, views
from django.contrib.auth import authenticate


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    role = serializers.ChoiceField(choices=[('publisher', 'Publisher'), ('reviewer', 'Reviewer')])  # 用户选择角色


class UserLoginView(views.APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            role = serializer.validated_data['role']  # 获取用户选择的角色
            user = authenticate(email=email, password=password)
            if user is not None:
                if user.role != role:
                    return Response({"message": f"Invalid role. User is not a {role}."},
                                    status=status.HTTP_400_BAD_REQUEST)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'role': user.role,
                    'organization': user.organization.name if user.organization else None,
                    'profile': user.profile,
                    'avatar': user.avatar.url
                })
            return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import views
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class UserLogoutView(views.APIView):
    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)

            # 标记 refresh token 为无效
            token.blacklist()

            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except KeyError:
            return Response({"message": "Refresh token missing"}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError as e:
            return Response({"message": f"Token error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import serializers
from django.contrib.auth import get_user_model


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'role', 'profile', 'avatar']  # 这里加入了 profile 字段

    username = serializers.CharField(required=False)  # 使 `username` 可选

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.role = validated_data.get('role', instance.role)
        instance.profile = validated_data.get('profile', instance.profile)  # 更新 profile 字段
        instance.avatar = validated_data.get('avatar', instance.avatar)  # 更新头像
        instance.save()
        return instance


from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import serializers, views
from django.contrib.auth import get_user_model
from rest_framework.decorators import permission_classes


@permission_classes([IsAuthenticated])
class UserUpdateView(views.APIView):
    authentication_classes = [JWTAuthentication]

    def put(self, request):
        try:
            user = request.user  # 获取当前认证的用户
            serializer = UserUpdateSerializer(user, data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                return Response({"message": "User information updated successfully"})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TokenRefreshView(views.APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')  # 从请求中获取 refresh token
            if refresh_token is None:
                return Response({"message": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            # 使用 refresh token 获取新的 access token
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)  # 获取新的 access token

            return Response({"access": new_access_token}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField(read_only=True)  # 动态获取组织名称

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'role', 'profile', 'avatar', 'permission', 'organization',
                  'organization_name']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None


from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import views


class UserDetailView(views.APIView):
    # 添加认证和授权
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # 获取当前认证的用户
        serializer = UserDetailSerializer(user)  # 使用序列化器返回用户的所有信息
        return Response(serializer.data)


from rest_framework import serializers
from django.contrib.auth import get_user_model


class AvatarUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['avatar']  # 只处理头像字段

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)  # 更新头像
        instance.save()
        return instance


from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import views, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser


class AvatarUpdateView(views.APIView):
    # 添加认证和授权
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    # 支持上传文件
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        user = request.user  # 获取当前认证的用户
        serializer = AvatarUpdateSerializer(user, data=request.data)

        if serializer.is_valid():
            serializer.save()  # 保存更新后的头像
            return Response({"message": "Avatar updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import serializers, views, status
from rest_framework.response import Response
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = get_user_model().objects.get(email=email)

                # 生成并设置验证码
                user.set_reset_code()

                # 发送重置密码的邮件
                send_mail(
                    'Password Reset Request',
                    f'Your password reset code is: {user.reset_code}',
                    '2406854677@qq.com',
                    [email],
                    fail_silently=False,
                )

                return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
            except get_user_model().DoesNotExist:
                return Response({"message": "Email not found."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework import serializers, views, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model


class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_code = serializers.CharField()  # 用户输入的验证码
    new_password = serializers.CharField()  # 用户输入的新密码


class PasswordResetConfirmView(views.APIView):
    permission_classes = [AllowAny]  # 允许任何用户调用该接口，不需要认证

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = request.data.get('email')
            try:
                # 获取用户
                user = get_user_model().objects.get(email=email)

                # 验证验证码
                if user.reset_code == serializer.validated_data['reset_code'] and user.is_reset_code_valid():
                    # 更新密码
                    new_password = serializer.validated_data['new_password']
                    user.set_password(new_password)
                    user.reset_code = None  # 清除验证码
                    user.reset_code_expiry = None  # 清除过期时间
                    user.save()
                    return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Invalid or expired reset code."}, status=status.HTTP_400_BAD_REQUEST)

            except get_user_model().DoesNotExist:
                return Response({"message": "Invalid email address."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from ..models import DetectionTask, DetectionResult


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_summary_lzy(request):
    user = request.user
    one_month_ago = timezone.now() - timedelta(days=30)

    user_id = request.user.id
    my_user = User.objects.get(id=user_id)

    # 获取用户的所有任务
    total_tasks = DetectionTask.objects.filter(organization=my_user.organization, user=user)
    completed_tasks = total_tasks.filter(status='completed')
    recent_tasks = total_tasks.filter(upload_time__gte=one_month_ago)

    # 统计任务数
    total_task_count = total_tasks.count()
    completed_task_count = completed_tasks.count()
    recent_task_count = recent_tasks.count()

    # 获取最近任务的详细信息（例如，任务上传时间和完成时间）
    task_details = []
    for task in recent_tasks:
        task_details.append({
            "task_id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "upload_time": timezone.localtime(task.upload_time),
            "completion_time": timezone.localtime(task.completion_time),
        })

    return Response({
        "total_task_count": total_task_count,
        "completed_task_count": completed_task_count,
        "recent_task_count": recent_task_count,
        "recent_tasks": task_details,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detection_task_status(request, task_id):
    try:
        user_id = request.user.id
        my_user = User.objects.get(id=user_id)

        # 获取任务和关联的检测结果
        detection_task = DetectionTask.objects.get(id=task_id, user=request.user)
        detection_results = DetectionResult.objects.filter(organization=my_user.organization, detection_task=detection_task)

        # 收集任务相关的图像和状态信息
        task_status = {
            "task_id": detection_task.id,
            "task_name": detection_task.task_name,
            "status": detection_task.status,
            "upload_time": timezone.localtime(detection_task.upload_time),
            "completion_time": timezone.localtime(detection_task.completion_time),
            "detection_results": []
        }

        for result in detection_results:
            task_status["detection_results"].append({
                "image_id": result.image_upload.id,
                "status": result.status,
                "is_fake": result.is_fake,
                "confidence_score": result.confidence_score,
                "detection_time": timezone.localtime(result.detection_time),
            })

        return Response(task_status)

    except DetectionTask.DoesNotExist:
        return Response({"message": "Detection task not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_user_tasks(request):
    try:
        user_id = request.user.id
        my_user = User.objects.get(id=user_id)
        # 获取当前认证用户的所有任务
        tasks = DetectionTask.objects.filter(organization=my_user.organization, user=request.user)

        # 收集任务信息
        task_data = []
        for task in tasks:
            task_data.append({
                "task_id": task.id,
                "task_name": task.task_name,
                "status": task.status,
                "upload_time": timezone.localtime(task.upload_time),
                "completion_time": timezone.localtime(task.completion_time),
            })

        return Response({
            "tasks": task_data
        })

    except DetectionTask.DoesNotExist:
        return Response({"message": "No tasks found for the user"}, status=404)


from rest_framework import views, status
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.utils import timezone
from ..models import Log, DetectionTask, DetectionResult


class SingleUserActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'user', 'operation_type', 'related_model', 'related_id', 'operation_time']


@permission_classes([IsAuthenticated])
class SingleUserActionLogView(views.APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        # 获取分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        publisher = request.GET.get('publisher', '')
        status = request.GET.get('status', '')  # 'completed' 或 'pending'
        start_time = request.GET.get('startTime', None)
        end_time = request.GET.get('endTime', None)

        # 获取当前用户的日志记录
        user_id = request.user.id
        my_user = User.objects.get(id=user_id)
        user = request.user
        logs = Log.objects.filter(organization=my_user.organization, user=user).order_by('-operation_time')

        # 应用筛选条件
        if publisher:
            logs = logs.filter(related_model='DetectionTask',
                               related_id__in=DetectionTask.objects.filter(publisher=publisher).values_list('id',
                                                                                                            flat=True))
        if status:
            logs = logs.filter(related_model='DetectionTask',
                               related_id__in=DetectionTask.objects.filter(status=status).values_list('id', flat=True))
        if start_time:
            logs = logs.filter(operation_time__gte=start_time)
        if end_time:
            logs = logs.filter(operation_time__lte=end_time)

        paginator = Paginator(logs, page_size)  # 每页显示指定数量的日志

        try:
            page_obj = paginator.page(page)
        except Exception:
            return Response({'error': 'Invalid page number'}, status=400)

        serializer = SingleUserActionLogSerializer(page_obj.object_list, many=True)

        return Response({
            'logs': serializer.data,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_logs': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        })


class ReviewerTasksView(views.APIView):
    """
    返回 editor 总共收到的任务数和已完成的任务数
    """

    def get(self, request):
        user = request.user
        user_id = request.user.id
        my_user = User.objects.get(id=user_id)

        if user.role != 'reviewer':
            return Response({'error': 'Only reviewers can view review details'}, status=403)

        # 获取所有分配给当前 reviewer 的任务 ID 列表（不设时间限制）
        assigned_tasks_ids = ReviewRequest.objects.filter(
            organization=my_user.organization,
            reviewers=user
        ).values_list('detection_result__detection_task_id', flat=True)

        # 所有收到的任务（关联 DetectionTask）
        received_tasks = DetectionTask.objects.filter(id__in=assigned_tasks_ids)

        # 所有已完成的任务（ManualReview 中状态为 completed）
        completed_tasks_ids = ManualReview.objects.filter(
            organization=my_user.organization,
            reviewer=user,
            status='completed'
        ).values_list('review_request__detection_result__detection_task_id', flat=True)

        completed_tasks = DetectionTask.objects.filter(id__in=completed_tasks_ids)

        # 统计总数
        total_received_tasks = received_tasks.count()
        total_completed_tasks = completed_tasks.count()

        return Response({
            'total_received_tasks': total_received_tasks,
            'total_completed_tasks': total_completed_tasks
        }, status=status.HTTP_200_OK)


class ReviewerActivityLogView(views.APIView):
    def get(self, request):
        user_id = request.user.id
        user = User.objects.get(id=user_id)
        if user.role != 'reviewer':
            return Response({'error': 'Only reviewers can view review details'}, status=403)

        # 获取最近7天的数据
        days_ago = timezone.now() - timezone.timedelta(days=7)

        # 查询 ManualReview 中 reviewer 为当前用户且 review_time 在最近7天内的记录
        manual_reviews = ManualReview.objects.filter(
            organization=user.organization,
            reviewer=user,
            review_time__gte=days_ago
        ).order_by('-review_time')

        result = []
        for review in manual_reviews:
            # 获取关联 DetectionTask 的 task_name
            detection_task = review.imgs.first().detection_task if review.imgs.exists() else None

            task_name = detection_task.task_name if detection_task else "Unknown Task"
            completion_time = review.review_time
            task_status = review.status

            result.append({
                'task_name': task_name,
                'completion_time': completion_time,
                'status': task_status
            })

        return Response(result, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usage_info(request):
    user = request.user
    remaining_uses = user.get_remaining_uses()

    return Response({
        "remaining_non_llm_uses": remaining_uses['remaining_non_llm_uses'],
        "remaining_llm_uses": remaining_uses['remaining_llm_uses'],
        "reset_time": remaining_uses['reset_time']
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization_usage_info(request):
    user = request.user
    organization = user.organization
    remaining_uses = organization.get_remaining_uses()

    return Response({
        "remaining_non_llm_uses": remaining_uses['remaining_non_llm_uses'],
        "remaining_llm_uses": remaining_uses['remaining_llm_uses'],
        # "reset_time": remaining_uses['reset_time']
    })

# 充值接口
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recharge_uses(request):
    user = request.user
    organization = user.organization
    remaining_uses = organization.get_remaining_uses()
    amount = request.data.get('amount', 0)  # 充值金额
    choice = request.data.get('choice', '').lower()

    num = int(amount) // 100

    if choice == "llm":
        organization.add_llm_uses(num * 3)
        message = f"充值成功，增加 {num * 3} 次 LLM 使用次数。"
    elif choice == "non-llm":
        organization.add_non_llm_uses(num * 100)
        message = f"充值成功，增加 {num * 100} 次非 LLM 使用次数。"
    else:
        return Response({"error": "无效的 choice 参数，应为 'llm' 或 'non-llm'"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": message,
        "remaining_non_llm_uses": organization.remaining_non_llm_uses,
        "remaining_llm_uses": organization.remaining_llm_uses,
    }, status=status.HTTP_200_OK)


import os
from django.conf import settings
from django.http import FileResponse
@api_view(['GET'])  # 明确指定允许的 HTTP 方法
def generate_manual_review_report_view(request, review_id):
    review = ManualReview.objects.get(id=review_id)
    report_path = generate_manual_review_report(review)
    # return Response({"report_url": review.report_file.url})

    # task = review.review_request.detection_result.image_upload.detection_task
    #
    # # 第一个报告
    # abs_path = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
    # if not os.path.exists(abs_path):
    #     return Response({"detail": "Report file missing."}, status=410)
    #
    # return FileResponse(open(abs_path, "rb"),
    #                     as_attachment=True,
    #                     filename=f"task_{task.id}_report.pdf")

    # 第二个报告
    abs_path = os.path.join(settings.MEDIA_ROOT, review.report_file.name)
    if not os.path.exists(abs_path):
        return Response({"detail": "Report file missing."}, status=410)

    return FileResponse(open(abs_path, "rb"),
                        as_attachment=True,
                        filename=f"manual_report.pdf")
# from io import BytesIO
# import zipfile
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def generate_manual_review_report_view(request, review_id):
#     # 获取模型对象
#     review = ManualReview.objects.get(id=review_id)
#     image_id = review.review_request.detection_result.image_upload.id
#
#     try:
#         detection_result = DetectionResult.objects.select_related('detection_task').get(
#             image_upload_id=image_id,
#         )
#     except DetectionResult.DoesNotExist:
#         return Response({"detail": "Image or task not found, or permission denied."}, status=404)
#     except DetectionResult.MultipleObjectsReturned:
#         return Response({"detail": "Multiple detection results found for this image."}, status=500)
#
#     print(review.review_request.detection_result.image_upload.id)
#     print(review.review_request.detection_result.id)
#     print(review.review_request.id)
#     task = detection_result.detection_task
#     print(task.id)
#
#     if task.status != "completed":
#         return Response({"detail": "Task not completed yet."}, status=400)
#
#     if not task.report_file:
#         return Response({"detail": "Report is still being generated."}, status=202)
#
#     # 两个报告的绝对路径
#     path1 = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
#     path2 = os.path.join(settings.MEDIA_ROOT, review.report_file.name)
#
#     # 检查文件是否存在
#     for p in (path1, path2):
#         if not os.path.exists(p):
#             return Response({"detail": f"Report file missing: {os.path.basename(p)}"}, status=410)
#
#     # 在内存中创建 zip 包
#     buffer = BytesIO()
#     with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#         # 第一个报告，指定压缩包内的文件名
#         zip_file.write(path1, arcname=f"task_{task.id}_report.pdf")
#         # 第二个报告
#         zip_file.write(path2, arcname="manual_report.pdf")
#
#     # 将指针移回开头
#     buffer.seek(0)
#
#     # 返回一个 FileResponse，浏览器会下载这个 zip
#     return FileResponse(
#         buffer,
#         as_attachment=True,
#         filename=f"reports.zip",
#         content_type='application/zip',
#     )