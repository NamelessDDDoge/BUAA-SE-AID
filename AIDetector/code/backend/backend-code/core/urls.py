from .views.views_organization import create_organization_root
from .views.views_review import get_manualReview_from_reviewRequestId
from .views.views_user import *
from .views.views_imageupload import *
from .views.views_dectection import *
# 新增: 导入人工审查相关的视图类
from .views import views_review, views_organization
from .views import views_admin
from .views import views_notify
from django.urls import path
from .views.views_admin import (
    AdminDashboardView,
    UserPermissionView,
    PostReportView,
    UserActionLogGetView,
    UserActionLogDeleteView,
    UserActionLogDownloadView,
    get_task_summary,
    get_detection_task_status,
    get_all_user_tasks,
    get_users,
    create_user,
    update_user,
    delete_user, AdminLoginView, create_admin,
    get_files,
    delete_upload, dashboard_img_tag, top_publishers_with_fake_ratio, top_organizations_with_fake_ratio, daily_active_users, daily_task_count,
    daily_review_request_count, daily_completed_manual_review_count, get_sub_method_distribution_by_tag,
    AdminDetailView, daily_active_organizations,
)
from . import views

urlpatterns = [
    # 用户相关的URL
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('user/update/', UserUpdateView.as_view(), name='update_user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/details/', UserDetailView.as_view(), name='user-details'),
    path('user/avatar/', AvatarUpdateView.as_view(), name='update-avatar'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('detection-task/<int:task_id>/status/', get_detection_task_status_normal, name='get_detection_task_status'),
    path('task-summary/', get_task_summary_lzy, name='get_task_summary_lzy'),
    path('get-task-summary/', get_task_summary, name='get_task_summary'),
    path('user-tasks/', get_user_tasks, name='get_user_tasks'),
    path('organization/usage/', get_organization_usage_info, name='get_usage_info'),
    path('organization/recharge-uses/', recharge_uses, name='recharge_uses'),
    path('single-user-action-log/', SingleUserActionLogView.as_view(), name='single_user_action_log'),
    path('reviewer/tasks/', ReviewerTasksView.as_view(), name='reviewer-tasks'),
    path('reviewer/activity_logs/', ReviewerActivityLogView.as_view(), name='reviewer-activity-logs'),
    path('manual-review/<int:review_id>/report/', generate_manual_review_report_view, name='generate_manual_review_report'),

    # 图片上传相关的URL
    path('upload/', upload_file, name='upload_file'),
    path('upload/<int:file_id>/', get_file_details, name='get_file_details'),
    path('upload/<int:file_id>/download/', download_uploaded_resource, name='download_uploaded_resource'),
    path('upload/<int:file_id>/preview_text/', get_resource_text_preview, name='get_resource_text_preview'),
    path('upload/<int:file_id>/extract_images/', get_extracted_images, name='get_extracted_images'),
    path('upload/<int:file_id>/addTag/', add_file_tag, name='add_file_tag'),
    path('upload/<int:file_id>/delete/', delete_upload, name='delete_upload'),
    path('upload/get_all_file_images/<int:file_management_id>/', get_all_file_images, name='get_all_file_images'),
    # 图片检测相关的URL
    path('detection/<int:image_id>/', get_detection_result, name='image_detection'),
    path('detection/submit/', submit_detection2, name='submit_detection'),
    path("paper-results/<int:task_id>/", get_paper_detection_results, name="paper-results"),
    path('resource-task/create/', create_resource_task, name='create_resource_task'),
    path("tasks/<int:task_id>/report/", download_task_report, name="download-task-report"),
    path("tasks_image/<int:image_id>/report/", download_image_report, name="download-image-report"),
    path("tasks_image/<int:image_id>/getdr/", image2dr, name="image2dr"),
    path("tasks/<int:task_id>/results/",   list_task_results,        name="task-results"),
    path("results/<int:result_id>/",       detection_result_detail,  name="result-detail"),
    path("results_image/<int:image_id>/", detection_result_by_image, name="result-image"),
    path("tasks/<int:task_id>/fake_results/", list_fake_task_results, name="fake-results"),
    path("tasks/<int:task_id>/normal_results/", list_normal_task_results, name="normal-results"),
    path("detection-task-delete/<int:task_id>/", DetectionTaskDeleteView.as_view(), name="delete-detection-task"),
    path("detection-history/clear/", DetectionHistoryClearView.as_view(), name="clear-detection-history"),

    # 新增: 人工审查相关的URL
    path('publishers/<int:publisher_id>/reviewers/', views_review.get_reviewers_for_publisher),
    path('create_review_task_with_admin_check/', views_review.create_review_task_with_admin_check, name='create_review_task_with_admin_check'),
    path('create_resource_review_task_placeholder/', views_review.create_resource_review_task_placeholder, name='create_resource_review_task_placeholder'),
    path('get_request_completion_status/<int:task_id>/', views_review.get_request_completion_status, name='get_request_completion_status'),
    path('get_request_detail/<int:reviewRequest_id>/', views_review.get_request_detail, name='get_request_detail'),
    path('get_reviewer_tasks/', views_review.get_reviewer_manual_request, name='get_reviewer_tasks'),
    path('get_all_reviewers/', views_review.get_all_reviewers_in_org, name='get_all_reviewers'),
    path('get_publisher_review_tasks/', views_review.get_publisher_review_tasks, name='get_publisher_review_tasks'),
    path('get_img_review_all/', views_review.get_img_review_all, name='get_img_review_all'),  # 新增路由
    path('get_image_review/', views_review.get_image_review, name='get_image_review'),  # 新增路由/api/get_image_review/?review_request_id=&img_id=&reviewer_id=
    path('get_review_detail/<int:manual_review_id>/', views_review.get_review_detail, name='get_review_detail'),  # 新增路由
    path('post_review/<int:manual_review_id>/', views_review.post_review, name='post_review'),  # 新增路由
    path('publisher-dectectiontask-access/', views_review.if_publisher_can_access_dectection_task, name='if_publisher_can_access_dectection_task'),
    path('reviewer-manualreview-access/', views_review.if_reviewer_can_access_manual_review, name='if_reviewer_can_access_manual_review'),
    path('get-reviewer-request-detail/<int:reviewRequest_id>/', views_review.get_reviewer_request_detail, name='get_reviewer_request_detail'),

    # 管理端URL配置
    path('admin/details/', AdminDetailView.as_view(), name='admin-details-default'),
    path('admin/details/<int:user_id>', AdminDetailView.as_view(), name='admin-details'),
    path('manage-associations/', views_admin.add_reviewer_to_publisher),

    # 仪表盘视图 dashboard部分
    path('admin_dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/img_tag/', dashboard_img_tag, name='dashboard_img_tag'),
    path('dashboard/top_publishers/', top_publishers_with_fake_ratio, name='top_publishers'),
    path('dashboard/top_organizations/', top_organizations_with_fake_ratio, name='top_organizations'),
    path('dashboard/daily_active_users/', daily_active_users, name='daily_active_users'),
    path('dashboard/daily_active_organizations/', daily_active_organizations, name='daily_active_organizations'),

    path('dashboard/daily_task_count/', daily_task_count, name='daily_task_count'),
    path('dashboard/daily_review_request_count/', daily_review_request_count, name='daily_review_request_count'),
    path('dashboard/daily_completed_manual_review_count/', daily_completed_manual_review_count, name='daily_completed_manual_review_count'),
    path('dashboard/get_sub_method_distribution_by_tag/', get_sub_method_distribution_by_tag, name='get_sub_method_distribution_by_tag'),

    # 用户权限管理视图
    path('user_permission/<int:user_id>/', UserPermissionView.as_view(), name='user_permission'),
    # 帖子举报处理视图
    path('post_report/<int:post_id>/', PostReportView.as_view(), name='post_report'),
    # 用户操作日志视图
    path('user_action_log/', UserActionLogGetView.as_view(), name='user_action_log'),
    path('user_action_log/<int:log_id>/', UserActionLogDeleteView.as_view(), name='delete_user_action_log'),
    path('user_action_log/download/', UserActionLogDownloadView.as_view(), name='download_user_action_log'),
    # 获取任务概览
    path('get_task_summary/', get_task_summary, name='get_task_summary'),
    # 获取检测任务状态
    path('get_detection_task_status/<int:task_id>/', get_detection_task_status, name='get_detection_task_status'),
    # 获取所有用户任务
    path('get_all_user_tasks/', get_all_user_tasks, name='get_all_user_tasks'),
    # 获取分页用户信息
    path('get_users/', get_users, name='get_users'),
    # 创建新用户
    path('create_user/', create_user, name='create_user'),
    # 更新用户信息
    path('update_user/<int:user_id>/', update_user, name='update_user'),
    # 删除用户
    path('delete_user/<int:user_id>/', delete_user, name='delete_user'),
    # 管理员登录
    path('admin-login/', AdminLoginView.as_view(), name='admin_login'),
    # 创建新管理员用户
    path('create-admin/', create_admin, name='create_admin'),
    # 获取文件列表
    path('get_files/', get_files, name='get_files'),
    path('get_reviewRequest/all/', views_admin.get_all_review_requests, name='get_all_review_requests'),
    path('get_reviewRequest/<int:reviewRequest_id>/', views_admin.get_review_request_detail_admin, name='get_review_request_detail_admin'),
    path('get_review_request_detail/<int:manual_review_id>/', views_admin.get_review_request_detail, name='get_review_request_detail'),
    path('handle_reviewRequest/<int:reviewRequest_id>/', views_admin.handle_review_request, name='handle_review_request'),
    path('delete_image_upload/<int:image_id>/', views_admin.delete_image_upload, name='delete_image_upload'),
    path('review-requests/<int:review_request_id>/delete/', views_admin.delete_review_request, name='get_image_upload'),

    # 通知部分
    path('notification/notify/', views_notify.get_notification_status, name='notification_status'),
    path('notification/set_as_read/', views_notify.set_notifications_as_read, name='set_notifications_read'),
    path('notification/get/', views_notify.get_notifications, name='get_notifications'),
    path('notification/set_as_read/<int:notification_id>/', views_notify.set_single_notification_as_read, name='set_single_notification_as_read'),
    path('notification/broadcast/', views_notify.broadcast_notification, name='broadcast_notification'),

    # 组织相关URL配置
    path('organizations/create-directly/', create_organization_root, name='create_organization_directly'),
    path('organization/create/', views_organization.CreateOrganizationApplicationView.as_view(), name='create_organization'),
    # 软件管理员查看所有待审核的组织申请
    path('organization/applications/get_pending/', views_organization.get_pending_organization_applications, name='get_pending_applications'),

    path('organization/applications/<int:app_id>/', views_organization.get_pending_organization_applications_detail, name='get_pending_organization_applications_detail'),
    path('organization/<int:app_id>/approve/', views_organization.approve_organization_application, name='approve_organization_application'),
    path('organization/<int:app_id>/reject/', views_organization.reject_organization_application, name='reject_organization_application'),
    path('organization/<int:org_id>/invitation_codes/', views_organization.GetInvitationCodesView.as_view(), name='get_invitation_codes'),
    path('organizations/', views_organization.get_organizations, name='get_organizations'),
    path('organization/<int:org_id>/', views_organization.get_organization_detail, name='get_organization_detail'),
    path('organization/<int:org_id>/delete/', views_organization.delete_organization, name='delete_organization'),
    path('organization/<int:org_id>/permission/', views_organization.update_organization_role_permissions, name='update_organization_role_permissions'),

    path('manual-review/<int:review_request_id>/', get_manualReview_from_reviewRequestId, name='get_manualReview_from_reviewRequestId'),

]
