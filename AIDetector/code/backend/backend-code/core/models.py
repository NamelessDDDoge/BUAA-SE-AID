from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser


class OrganizationApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    admin_username = models.CharField(max_length=150)
    admin_email = models.EmailField()
    admin_password = models.CharField(max_length=128)  # 可加密存储
    proof_materials = models.FileField(upload_to='proof_materials/', null=True, blank=True)
    logo = models.ImageField(upload_to='organization_logos/', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(default=timezone.localtime)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewer = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, related_name='handled_applications')

    def __str__(self):
        return f"{self.name} (Status: {self.status})"


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    admin_user = models.OneToOneField('core.User', on_delete=models.CASCADE, related_name='admin_organization', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.localtime)

    description = models.TextField(blank=True, null=True)  # 组织描述
    logo = models.ImageField(upload_to='organization_logos/', null=True, blank=True)  # LOGO
    proof_materials = models.FileField(upload_to='proof_materials/', null=True, blank=True)  # 证明材料

    # 新增字段：用于记录每个组织的 LLM 和非 LLM 方法的剩余次数
    remaining_non_llm_uses = models.PositiveIntegerField(default=100)
    remaining_llm_uses = models.PositiveIntegerField(default=3)
    last_reset_time = models.DateTimeField(null=True, blank=True)

    def reset_usage(self):
        return
        """每周重置组织内所有用户共享的次数"""
        if not self.last_reset_time or self.last_reset_time + timedelta(weeks=1) < timezone.now():
            self.remaining_non_llm_uses = 100
            self.remaining_llm_uses = 3
            self.last_reset_time = timezone.now()
            self.save()

    def can_use_non_llm(self, num_images):
        """检查组织是否有足够的非 LLM 方法检测次数"""
        self.reset_usage()
        return self.remaining_non_llm_uses >= num_images

    def can_use_llm(self, num_images):
        """检查组织是否有足够的 LLM 方法检测次数"""
        self.reset_usage()
        return self.remaining_llm_uses >= num_images

    def decrement_non_llm_uses(self, num_images):
        """减少组织的非 LLM 方法检测次数"""
        if self.can_use_non_llm(num_images):
            self.remaining_non_llm_uses -= num_images
            self.save()

    def add_non_llm_uses(self, num_images):
        """增加组织的非 LLM 方法检测次数"""
        self.remaining_non_llm_uses += num_images
        self.save()

    def decrement_llm_uses(self, num_images):
        """减少组织的 LLM 方法检测次数"""
        if self.can_use_llm(num_images):
            self.remaining_llm_uses -= num_images
            self.save()

    def add_llm_uses(self, num_images):
        """增加组织的 LLM 方法检测次数"""
        self.remaining_llm_uses += num_images
        self.save()

    def get_remaining_uses(self):
        """返回组织剩余的检测次数及重置时间"""
        self.reset_usage()
        return {
            'remaining_non_llm_uses': self.remaining_non_llm_uses,
            'remaining_llm_uses': self.remaining_llm_uses,
            'reset_time': self.last_reset_time + timedelta(weeks=1) if self.last_reset_time else None
        }

    def __str__(self):
        return self.name


class InvitationCode(models.Model):
    ROLE_CHOICES = (
        ('publisher', 'Publisher'),
        ('reviewer', 'Reviewer'),
    )
    code = models.CharField(max_length=6, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.organization.name} - {self.role}"


class User(AbstractUser):
    ROLES = (
        ('admin', 'Admin'),
        ('publisher', 'Publisher'),
        ('reviewer', 'Reviewer'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    role = models.CharField(
        max_length=50,
        choices=ROLES,
        default='publisher'
    )

    # 添加多对多关系（对称关系设为False避免自关联冲突）
    related_reviewers = models.ManyToManyField(
        'self',
        through='core.PublisherReviewerRelationship',
        symmetrical=False,
        related_name='related_publishers',
        limit_choices_to={'role': 'reviewer'}
    )

    # 其他字段保持不变...
    permission = models.IntegerField(null=True)  # 权限筛选,四位分别代表：上传，提交，发布，审核(例如，publisher默认为1110，reviewer默认为1）
    profile = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, default='avatars/default.png')
    reset_code = models.CharField(max_length=6, null=True, blank=True)
    reset_code_expiry = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(unique=True)
    remaining_non_llm_uses = models.PositiveIntegerField(default=100)
    remaining_llm_uses = models.PositiveIntegerField(default=3)
    last_reset_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def reset_usage(self):
        """每周重置次数"""
        if not self.last_reset_time or self.last_reset_time + timedelta(weeks=1) < timezone.now():
            self.remaining_non_llm_uses = 100
            self.remaining_llm_uses = 3
            self.last_reset_time = timezone.now()
            self.save()

    def can_use_non_llm(self, num_images):
        """检查用户是否有足够的非 LLM 方法检测次数"""
        self.reset_usage()
        return self.remaining_non_llm_uses >= num_images

    def can_use_llm(self, num_images):
        """检查用户是否有足够的 LLM 方法检测次数"""
        self.reset_usage()
        return self.remaining_llm_uses >= num_images

    def decrement_non_llm_uses(self, num_images):
        """减少非 LLM 方法检测次数"""
        if self.can_use_non_llm(num_images):
            self.remaining_non_llm_uses -= num_images
            self.save()

    def decrement_llm_uses(self, num_images):
        """减少 LLM 方法检测次数"""
        if self.can_use_llm(num_images):
            self.remaining_llm_uses -= num_images
            self.save()

    def get_remaining_uses(self):
        """返回用户剩余的检测次数及重置时间"""
        self.reset_usage()
        return {
            'remaining_non_llm_uses': self.remaining_non_llm_uses,
            'remaining_llm_uses': self.remaining_llm_uses,
            'reset_time': self.last_reset_time + timedelta(weeks=1) if self.last_reset_time else None
        }

    def save(self, *args, **kwargs):
        # 设置权限
        if self.role == 'publisher':
            self.permission = 1110
        elif self.role == 'reviewer':
            self.permission = 1
        else:
            self.permission = None
        super().save(*args, **kwargs)

    def save_permission(self, *args, **kwargs):
        # 设置权限
        super().save(*args, **kwargs)

    def set_reset_code(self):
        """生成6位验证码，并设置过期时间为10分钟后"""
        import random
        self.reset_code = str(random.randint(100000, 999999))
        self.reset_code_expiry = timezone.now() + timedelta(minutes=10)
        self.save()

    def is_reset_code_valid(self):
        """检查验证码是否有效，且未过期"""
        if self.reset_code and self.reset_code_expiry > timezone.now():
            return True
        return False

    def has_permission(self, perm_type):
        if self.permission is None:
            return False
        if not self.organization:  # 新增组织存在性检查
            return False
        perm_str = str(self.permission).zfill(4)  # 补足4位
        perms = {
            'upload': perm_str[0] == '1',
            'submit': perm_str[1] == '1',
            'publish': perm_str[2] == '1',
            'review': perm_str[3] == '1'
        }
        return perms.get(perm_type, False)


# 中间表模型（可扩展关系属性）
class PublisherReviewerRelationship(models.Model):
    publisher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='publisher_relationships',
        limit_choices_to={'role': 'publisher'}
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviewer_relationships',
        limit_choices_to={'role': 'reviewer'}
    )
    created_at = models.DateTimeField(default=timezone.localtime)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('publisher', 'reviewer')  # 防止重复关联


class FileManagement(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('paper', 'Paper'),
        ('review_paper', 'ReviewPaper'),
        ('review_file', 'ReviewFile')
    ]

    TAG_CHOICES = [
        ('Biology', 'Biology'),
        ('Medicine', 'Medicine'),
        ('Chemistry', 'Chemistry'),
        ('Graphics', 'Graphics'),
        ('Other', 'Other')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_type = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, default='image', db_index=True)
    linked_file = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_children')
    stored_path = models.CharField(max_length=500, default='', blank=True)
    upload_time = models.DateTimeField(default=timezone.localtime)
    tag = models.CharField(max_length=20, choices=TAG_CHOICES, default='Other')

    def __str__(self):
        return f"File {self.file_name} uploaded by {self.user.username}"


class DetectionTask(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    TASK_TYPE_CHOICES = [
        ('image', 'Image'),
        ('paper', 'Paper'),
        ('review', 'Review'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 任务属于哪个用户
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='image', db_index=True)
    task_name = models.CharField(max_length=255)  # 任务名称，用户可以自定义
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')  # 任务状态
    upload_time = models.DateTimeField(default=timezone.localtime)  # 上传时间
    completion_time = models.DateTimeField(null=True, blank=True)  # 完成时间（如果已完成）
    error_message = models.TextField(null=True, blank=True)
    resource_files = models.ManyToManyField(FileManagement, related_name='detection_tasks', blank=True)
    report_file = models.FileField(upload_to='reports/', null=True, blank=True,
                                   help_text='生成的 PDF 检测报告')
    # 记录参数，包括cmd_block_size（整数） urn_k（小数） if_use_llm（True或False）
    cmd_block_size = models.IntegerField(null=True, blank=True)
    urn_k = models.FloatField(null=True, blank=True)
    if_use_llm = models.BooleanField(default=False)  # 是否使用大语言模型
    method_switches = models.JSONField(null=True, blank=True)  # 子任务开关映射 {"ela": true, "exif": false, ...}，传入后覆盖 Config.py 默认值
    text_detection_results = models.JSONField(null=True, blank=True)  # 用于存储文本检测分段结果

    def __str__(self):
        return f"Task {self.id} - {self.user.username}"


class ImageUpload(models.Model):
    detection_task = models.ForeignKey(DetectionTask, on_delete=models.CASCADE, related_name='image_uploads',
                                       null=True)  # 关联任务
    file_management = models.ForeignKey(FileManagement, on_delete=models.CASCADE, related_name='image_uploads')
    image = models.ImageField(upload_to='extracted_images/')  # 存储提取出的图片
    extracted_from_pdf = models.BooleanField(default=False)  # 标记是否来自PDF提取
    page_number = models.IntegerField(null=True, blank=True)  # 对于PDF文件，记录该图片是哪个页面
    upload_time = models.DateTimeField(default=timezone.localtime)
    isDetect = models.BooleanField(default=False)  # 是否已提交AI检测
    isReview = models.BooleanField(default=False)  # 是否已提交人工审核
    isFake = models.BooleanField(default=False)  # AI检测结果，是否为假图

    def __str__(self):
        return f"Image {self.id} from file {self.file_management.file_name}"


class DetectionResult(models.Model):
    STATUS_CHOICES = [
        ('in_progress', '正在检测中'),
        ('completed', '检测已完成'),
        ('failed', '检测失败'),
    ]

    image_upload = models.ForeignKey(ImageUpload, on_delete=models.CASCADE, related_name="detection_results")
    is_fake = models.BooleanField(null=True)  # AI检测结果（是否为造假），初始为null
    confidence_score = models.FloatField(null=True)  # AI检测可信度，初始为null
    detection_time = models.DateTimeField(null=True, blank=True)  # 检测时间，初始为null
    is_under_review = models.BooleanField(default=False)  # 是否正在审核
    review_request = models.OneToOneField('ReviewRequest', null=True, blank=True,
                                          on_delete=models.SET_NULL)  # 外键，指向ReviewRequest表
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')  # 新增字段：状态
    detection_task = models.ForeignKey('DetectionTask', on_delete=models.CASCADE,
                                       related_name='detection_results', null=True)  # 关联到DetectionTask
    # ─── LLM / ELA / EXIF 补充信息 ──────────────────────────────────────────
    llm_judgment = models.TextField(null=True, blank=True,
                                    help_text='大语言模型生成的文字判断结果')
    ela_image = models.ImageField(
        upload_to='ela_results/', null=True, blank=True,
        help_text='ELA 算法产生的可视化图像')
    llm_image = models.ImageField(
        upload_to='llm_results/', null=True, blank=True,
        help_text='LLM 产生的可视化图像')
    exif_photoshop = models.BooleanField(
        null=True, help_text='EXIF 判定：是否用 Photoshop 修改')
    exif_time_modified = models.BooleanField(
        null=True, help_text='EXIF 判定：是否修改拍摄 / 创建时间')

    def __str__(self):
        return f"Detection result for {self.image_upload.id}"


# 7 种子检测方法的逐项记录
SUB_METHOD_CHOICES = [
    ('method1', 'Method-1'),
    ('method2', 'Method-2'),
    ('method3', 'Method-3'),
    ('method4', 'Method-4'),
    ('method5', 'Method-5'),
    ('method6', 'Method-6'),
    ('method7', 'Method-7'),
]


class SubDetectionResult(models.Model):
    detection_result = models.ForeignKey(
        DetectionResult, on_delete=models.CASCADE, related_name='sub_results')
    method = models.CharField(max_length=30, choices=SUB_METHOD_CHOICES)
    probability = models.FloatField()

    # mask 既保存可视化图，又保存 256×256 源矩阵
    mask_image = models.ImageField(upload_to='masks/', null=True, blank=True)
    mask_matrix = models.JSONField()  # MariaDB 10.3 可以；底层 LONGTEXT

    created_at = models.DateTimeField(default=timezone.localtime)

    class Meta:
        unique_together = ('detection_result', 'method')  # 一张图一方法唯一一条

    def __str__(self):
        return f"{self.method} of DetectionResult #{self.detection_result_id}"


class ReviewRequest(models.Model):
    detection_result = models.ForeignKey(DetectionResult, on_delete=models.CASCADE, related_name='review_requests')
    imgs = models.ManyToManyField(ImageUpload, related_name='review_requests')  # 新增字段：与ImageUpload的一对多关系
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 提交审核请求的用户
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    # request_time = models.DateTimeField(default=timezone.localtime, db_index=True)  # 申请时间，添加索引
    request_time = models.DateTimeField(default=timezone.localtime, db_index=True)
    # request_time = timezone.localtime(timezone.now())  # 申请时间，添加索引
    
    # 发布者状态，pending表示待管理员审核，in_progress表示审稿人审核中，completed表示审核完成
    status1 = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('in_progress', 'In Progress'),
                                                       ('completed', 'Completed')], default='pending')

    reason = models.TextField()  # 用户申请审核的原因
    review_start_time = models.DateTimeField(null=True, blank=True)  # 审核开始时间
    review_end_time = models.DateTimeField(null=True, blank=True)  # 审核结束时间

    reviewers = models.ManyToManyField(User, related_name='review_requests', blank=True)  # 指定的审核人员列表

    status2 = models.CharField(max_length=50,
                               choices=[('pending', 'Pending'), ('refused', 'Refused'), ('accepted', 'Accepted')],
                               default='pending')  # 管理员状态
    check_reason = models.TextField()  # 管理员审核的理由

    def __str__(self):
        return f"Review Request for Detection {self.detection_result.id} by {self.user.username}"


class ManualReview(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True, null=True, blank=True)
    review_request = models.ForeignKey(ReviewRequest, on_delete=models.CASCADE, related_name='manual_reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')  # 参与审核的审核员
    status = models.CharField(max_length=50, choices=[('undo', 'Undo'), ('completed', 'Completed')],
                              default='undo')  # 审核状态
    imgs = models.ManyToManyField(ImageUpload, related_name='manual_reviews')  # 关联的图片
    img_reviews = models.ManyToManyField('ImageReview', related_name='manual_reviews')  # 关联的ImageReview
    review_time = models.DateTimeField(default=timezone.localtime, db_index=True)  # 审核时间，添加索引
    report_file = models.FileField(upload_to='reports/', null=True, blank=True,
                                   help_text='生成的 PDF 检测报告')
    def __str__(self):
        return f"Review by {self.reviewer.username} on {self.review_request.detection_result.detection_task.id}"


class ImageReview(models.Model):
    manual_review = models.ForeignKey(ManualReview, on_delete=models.CASCADE, related_name='image_reviews')
    img = models.ForeignKey(ImageUpload, on_delete=models.CASCADE, related_name='image_reviews')

    score1 = models.IntegerField(null=True, blank=True)
    score2 = models.IntegerField(null=True, blank=True)
    score3 = models.IntegerField(null=True, blank=True)
    score4 = models.IntegerField(null=True, blank=True)
    score5 = models.IntegerField(null=True, blank=True)
    score6 = models.IntegerField(null=True, blank=True)
    score7 = models.IntegerField(null=True, blank=True)

    reason1 = models.TextField(blank=True, null=True)
    reason2 = models.TextField(blank=True, null=True)
    reason3 = models.TextField(blank=True, null=True)
    reason4 = models.TextField(blank=True, null=True)
    reason5 = models.TextField(blank=True, null=True)
    reason6 = models.TextField(blank=True, null=True)
    reason7 = models.TextField(blank=True, null=True)

    points1 = models.JSONField(null=True, blank=True)  # 新增：对应 method-1 的点集
    points2 = models.JSONField(null=True, blank=True)  # 新增：对应 method-2 的点集
    points3 = models.JSONField(null=True, blank=True)  # 新增：对应 method-3 的点集
    points4 = models.JSONField(null=True, blank=True)  # 新增：对应 method-4 的点集
    points5 = models.JSONField(null=True, blank=True)  # 新增：对应 method-5 的点集
    points6 = models.JSONField(null=True, blank=True)  # 新增：对应 method-6 的点集
    points7 = models.JSONField(null=True, blank=True)  # 新增：对应 method-7 的点集

    result = models.BooleanField(null=True)  # 最后的判定真假结果
    review_time = models.DateTimeField(default=timezone.localtime, db_index=True)  # 审核时间，添加索引


class Feedback(models.Model):
    manual_review = models.ForeignKey(ManualReview, on_delete=models.CASCADE, related_name="feedbacks")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedbacks")
    is_like = models.BooleanField(default=False)  # 是否点赞
    comment = models.TextField(blank=True, null=True)  # 评论内容
    feedback_time = models.DateTimeField(default=timezone.localtime)

    def __str__(self):
        return f"Feedback by {self.user.username} on review {self.manual_review.id}"


class Log(models.Model):
    OPERATION_TYPES = [
        ('upload', 'Upload'),
        ('detection', 'Detection'),
        ('review_request', 'Review Request'),
        ('manual_review', 'Manual Review')
    ]

    operation_time = models.DateTimeField(default=timezone.localtime)  # 记录操作时间
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPES)  # 操作类型
    related_model = models.CharField(max_length=50)  # 操作关联的模型名称
    related_id = models.IntegerField()  # 操作相关的模型ID，表的ID值

    def __str__(self):
        return f"{self.user.username} {self.operation_type} at {self.operation_time}"


class Notification(models.Model):
    GLOBAL = 1
    SYSTEM = 2
    P2R = 3
    R2P = 4

    CATEGORY_CHOICES = (
        (GLOBAL, 'GLOBAL'),
        (SYSTEM, 'SYSTEM'),
        (P2R, 'P2R'),
        (R2P, 'R2P'),
    )

    STATUS_CHOICES = (
        ('read', '已读'),
        ('unread', '未读'),
    )

    # 收件人信息
    receiver_id = models.CharField(max_length=100)
    receiver_name = models.CharField(max_length=100)

    # 发件人信息
    sender_id = models.CharField(max_length=100, null=True, blank=True)
    sender_name = models.CharField(max_length=100, null=True, blank=True)

    category = models.IntegerField(choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread')
    notified_at = models.DateTimeField(default=timezone.now)

    url = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-notified_at']

    def __str__(self):
        return f"{self.get_category_display()} - {self.title}"
