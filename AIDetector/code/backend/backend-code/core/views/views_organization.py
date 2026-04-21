from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Organization, InvitationCode, User, OrganizationApplication
import random
import string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from core.models import Organization
from django.core.paginator import Paginator
from django.db.models import Count
from django.db import models
from django.db.models import Count, F


class CreateOrganizationApplicationView(views.APIView):
    def post(self, request):
        org_name = request.data.get('name')
        email = request.data.get('email')

        admin_username = request.data.get('admin_username')
        admin_email = request.data.get('admin_email')
        admin_password = request.data.get('admin_password')

        proof_materials = request.FILES.get('proof_materials')
        logo = request.FILES.get('logo')
        description = request.data.get('description', '')

        if not all([org_name, email, admin_username, admin_email, admin_password]):
            return Response({"message": "All required fields must be provided"}, status=status.HTTP_400_BAD_REQUEST)

        # if User.objects.filter(username=admin_username).exists() or User.objects.filter(email=admin_email).exists():
        #     return Response({"message": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建组织申请记录
        application = OrganizationApplication.objects.create(
            name=org_name,
            email=email,
            admin_username=admin_username,
            admin_email=admin_email,
            admin_password=admin_password,
            proof_materials=proof_materials,
            logo=logo,
            description=description
        )

        return Response({
            "message": "Organization application submitted for review",
            "application_id": application.id
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_pending_organization_applications_detail(request, app_id):
    if request.user.email != 'admin@mail.com':
        return Response({"error": "Permission denied"}, status=403)

    try:
        app = OrganizationApplication.objects.get(id=app_id)

        return Response({
            'id': app.id,
            'name': app.name,
            'email': app.email,
            'admin_username': app.admin_username,
            'admin_email': app.admin_email,
            'description': app.description,
            'logo': app.logo.url if app.logo else None,
            'submitted_at': app.submitted_at,
            'proof_materials': app.proof_materials.url if app.proof_materials else None,
        })
    except OrganizationApplication.DoesNotExist:
        return Response({"error": "OrganizationApplication not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_pending_organization_applications(request):
    if request.user.email != 'admin@mail.com':
        return Response({"error": "Permission denied"}, status=403)

    # 获取查询参数
    query = request.query_params.get('query', '')  # 按组织名或管理员邮箱模糊搜索
    start_time = request.query_params.get('startTime')  # 起始时间
    end_time = request.query_params.get('endTime')  # 结束时间
    page = int(request.query_params.get('page', 1))  # 当前页码
    page_size = int(request.query_params.get('page_size', 10))  # 每页数量

    # 构建基础查询，并按 submitted_at 倒序排列（最新的在最前面）
    applications = OrganizationApplication.objects.filter(status='pending').order_by('-submitted_at')  # ✅ 修改点

    # 应用搜索条件
    if query:
        applications = applications.filter(
            models.Q(name__icontains=query) |
            models.Q(admin_email__icontains=query)
        )

    # 时间筛选
    if start_time:
        try:
            start_time = timezone.datetime.fromisoformat(start_time)
            applications = applications.filter(submitted_at__gte=start_time)
        except ValueError:
            return Response({'error': 'Invalid startTime format'}, status=400)

    if end_time:
        try:
            end_time = timezone.datetime.fromisoformat(end_time)
            applications = applications.filter(submitted_at__lte=end_time)
        except ValueError:
            return Response({'error': 'Invalid endTime format'}, status=400)

    # 分页处理
    paginator = Paginator(applications, page_size)

    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=400)

    # 序列化数据
    data = [{
        'id': app.id,
        'name': app.name,
        'email': app.email,
        'admin_username': app.admin_username,
        'admin_email': app.admin_email,
        'submitted_at': app.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
    } for app in page_obj.object_list]

    return Response({
        'applications': data,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_organization_application(request, app_id):
    try:
        application = OrganizationApplication.objects.get(id=app_id, status='pending')
    except OrganizationApplication.DoesNotExist:
        return Response({"error": "Application not found or already processed"}, status=404)

    if request.user.email != 'admin@mail.com':
        return Response({"error": "Only the software admin can approve applications"}, status=403)

    try:
        # 创建管理员用户
        admin_user = User.objects.create_user(
            username=application.admin_username,
            password=application.admin_password,
            email=application.admin_email,
            role='admin',
            organization=None
        )
        admin_user.is_staff = True
        admin_user.save()

        # 创建组织
        organization = Organization.objects.create(
            name=application.name,
            email=application.email,
            proof_materials=application.proof_materials,
            logo=application.logo,
            description=application.description,
            admin_user=admin_user
        )

        # 更新用户组织字段
        admin_user.organization = organization
        admin_user.save(update_fields=['organization'])

        # 生成邀请码
        def generate_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        InvitationCode.objects.create(
            code=generate_code(),
            organization=organization,
            role='publisher',
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        InvitationCode.objects.create(
            code=generate_code(),
            organization=organization,
            role='reviewer',
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        # 发送邮件通知
        subject = '组织创建成功 - 管理员账户信息'
        message = f"""
        您好，

        您的组织已审核通过并成功创建。以下是管理员账户信息：

        用户名: {admin_user.username}
        邮箱: {admin_user.email}

        此致
        敬礼
        """
        send_mail(subject, message, '2406854677@qq.com', [application.email, admin_user.email], fail_silently=False)

        # 标记为已通过
        application.status = 'approved'
        application.reviewer = request.user
        application.save()

        return Response({
            "message": "Organization approved successfully",
            "organization_id": organization.id
        })

    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_organization_application(request, app_id):
    try:
        application = OrganizationApplication.objects.get(id=app_id, status='pending')
    except OrganizationApplication.DoesNotExist:
        return Response({"error": "Application not found or already processed"}, status=404)

    if request.user.email != 'admin@mail.com':
        return Response({"error": "Only the software admin can reject applications"}, status=403)

    application.status = 'rejected'
    application.reviewer = request.user
    application.save()

    return Response({"message": "Organization application rejected"})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_organization_root(request):
    admin_email = request.data.get('admin_email')
    admin_username = request.data.get('admin_username')
    admin_password = request.data.get('admin_password')
    org_name = request.data.get('org_name')
    email = request.data.get('email')
    description = request.data.get('description', '')
    logo = request.FILES.get('logo')
    proof_materials = request.FILES.get('proof_materials')

    # 验证必填字段
    if not all([admin_email, admin_username, admin_password, org_name, email]):
        return Response({"message": "All required fields must be provided"}, status=status.HTTP_400_BAD_REQUEST)

    # 检查是否是根管理员
    if request.user.email != 'admin@mail.com':
        return Response({"error": "Permission denied"}, status=403)

    try:
        # 创建管理员用户
        admin_user = User.objects.create_user(
            username=admin_username,
            password=admin_password,
            email=admin_email,
            role='admin',
            organization=None
        )
        admin_user.is_staff = True
        admin_user.save()

        # 创建组织
        organization = Organization.objects.create(
            name=org_name,
            email=email,
            description=description,
            logo=logo,
            proof_materials=proof_materials,
            admin_user=admin_user
        )

        # 更新用户组织字段
        admin_user.organization = organization
        admin_user.save(update_fields=['organization'])

        # 生成邀请码
        def generate_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        InvitationCode.objects.create(
            code=generate_code(),
            organization=organization,
            role='publisher',
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        InvitationCode.objects.create(
            code=generate_code(),
            organization=organization,
            role='reviewer',
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        # 发送邮件通知
        subject = '组织已成功创建 - 管理员账户信息'
        message = f"""
        您好，

        您的组织已成功创建。以下是管理员账户信息：

        用户名: {admin_user.username}
        邮箱: {admin_user.email}

        此致
        敬礼
        """
        send_mail(subject, message, '2406854677@qq.com', [admin_user.email], fail_silently=False)

        return Response({
            "message": "Organization created successfully",
            "organization_id": organization.id
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetInvitationCodesView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, org_id):
        try:
            organization = Organization.objects.get(id=org_id)
            if request.user != organization.admin_user:
                return Response({"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

            codes = organization.invitationcode_set.all()
            data = [{"code": c.code, "role": c.role, "expires_at": c.expires_at} for c in codes]
            return Response(data)
        except Organization.DoesNotExist:
            return Response({"message": "Organization not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_organizations(request):
    query = request.query_params.get('query', '')
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))

    # 查询组织并预取用户和图片数量，并按 created_at 倒序排列（最新的在前）
    organizations = Organization.objects.all().order_by('-created_at')  # 修改点：倒序排列

    if query:
        organizations = organizations.filter(name__icontains=query)

    # 注入用户数和图像数
    organizations = organizations.annotate(
        user_count=Count('user', distinct=True),
        image_count=Count('user__filemanagement__image_uploads', distinct=True)
    )

    paginator = Paginator(organizations, page_size)

    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=400)

    data = []
    for org in page_obj.object_list:
        data.append({
            'id': org.id,
            'name': org.name,
            'description': org.description or '',
            'logo': org.logo.url if org.logo else None,
            'user_count': org.user_count,
            'image_count': org.image_count,
        })

    return Response({
        'organizations': data,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_organizations': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_organization(request, org_id):
    try:
        organization = Organization.objects.get(id=org_id)
        organization.delete()
        return Response({"message": "Organization deleted successfully"}, status=200)
    except Organization.DoesNotExist:
        return Response({"error": "Organization not found"}, status=404)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_organization_detail(request, org_id):
    try:
        organization = Organization.objects.annotate(
            user_count=Count('user'),
            image_count=Count('user__filemanagement__image_uploads', distinct=True)
        ).get(id=org_id)

        return Response({
            'id': organization.id,
            'name': organization.name,
            'email': organization.email,
            'created_at': organization.created_at,
            'description': organization.description or '',
            'logo': organization.logo.url if organization.logo else None,
            'proof_materials': organization.proof_materials.url if organization.proof_materials else None,
            'user_count': organization.user_count,
            'image_count': organization.image_count,
        })
    except Organization.DoesNotExist:
        return Response({"error": "Organization not found"}, status=404)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_organization_role_permissions(request, org_id):
    try:
        organization = Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return Response({"error": "Organization not found"}, status=404)

    role = request.data.get('role')  # publisher/reviewer
    permission_value = request.data.get('permission')

    if role not in ['publisher', 'reviewer']:
        return Response({"error": "Invalid role"}, status=400)

    try:
        permission_value = int(permission_value)
    except (TypeError, ValueError):
        return Response({"error": "Permission must be an integer"}, status=400)

    # 更新该组织下所有指定角色用户的权限
    users = User.objects.filter(organization=organization, role=role)
    users.update(permission=permission_value)

    return Response({"message": f"{role} permissions updated successfully"})
