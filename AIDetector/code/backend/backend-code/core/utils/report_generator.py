# utils/report_generator.py
import os, textwrap, json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..models import DetectionTask, DetectionResult, SubDetectionResult

# ─── 字体注册（宋体） ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_SIMSUN = "C:/Windows/Fonts/simsun.ttc"
FONT_SIMSUN_BOLD = "C:/Windows/Fonts/simsunb.ttf"
pdfmetrics.registerFont(TTFont('SimSun', FONT_SIMSUN))  # 中文字体
pdfmetrics.registerFont(TTFont('SimSun-Bold', FONT_SIMSUN_BOLD))  # 中文加粗字体


# ─── 工具函数：自动换行绘制 ───────────────────────────────
def _draw_multiline(c, x, y, text, max_chars=48, leading=14, font='SimSun', size=9):
    c.setFont(font, size)
    for line in textwrap.wrap(text, width=max_chars):
        c.drawString(x, y, line)
        y -= leading
    return y


MAX_CONTENT_HEIGHT = 40


def _check_and_create_new_page(c, y, H, MARGIN):
    """检查剩余空间，若不足则创建新页面"""
    if y - MAX_CONTENT_HEIGHT < MARGIN:
        c.showPage()  # 新页面
        y = H - MARGIN  # 重置 y 坐标
    return y


def generate_detection_task_report(task: DetectionTask) -> str:
    """
    生成 PDF 报告（中文），返回相对路径，并写入 task.report_file
    """
    # 生成路径
    rel_path = f"reports/task_{task.id}_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # 画布
    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    # ────────────────────────── 封面页 ──────────────────────────
    c.bookmarkPage("cover")
    c.addOutlineEntry("任务概览", "cover", level=0)

    y = H - 120
    c.setFont("SimSun-Bold", 40)
    c.drawCentredString(W / 2, y, '“听泉鉴图”图像造假检测报告')
    y -= 80

    c.setFont("SimSun", 24)
    c.drawString(MARGIN, y, f"任务编号：{task.id}")
    y -= 40
    c.drawString(MARGIN, y, f"任务名称：{task.task_name}")
    y -= 40
    c.drawString(MARGIN, y, f"用户：{task.user.username}")
    y -= 40

    create_time = timezone.localtime(task.upload_time).strftime("%Y-%m-%d %H:%M")
    finish_time = task.completion_time and timezone.localtime(task.completion_time).strftime("%Y-%m-%d %H:%M")
    c.drawString(MARGIN, y, f"创建时间：{create_time}")
    y -= 40
    if finish_time:
        c.drawString(MARGIN, y, f"完成时间：{finish_time}")
        y -= 40

    # 参数
    y -= 10
    c.setFont("SimSun-Bold", 24)
    c.drawString(MARGIN, y, "检测参数")
    y -= 36
    c.setFont("SimSun", 22)
    c.drawString(MARGIN, y, f"cmd_block_size：{task.cmd_block_size}")
    y -= 36
    c.drawString(MARGIN, y, f"urn_k：{task.urn_k}")
    y -= 36
    c.drawString(MARGIN, y, f"使用大语言模型：{'是' if task.if_use_llm else '否'}")

    c.showPage()

    # ─────────────────────── 每张图片一页 ──────────────────────
    for idx, dr in enumerate(
            task.detection_results.select_related("image_upload").prefetch_related("sub_results").order_by("id"),
            start=1
    ):
        page_label = f"图片 {dr.image_upload.id}"
        c.bookmarkPage(f"img_{dr.image_upload.id}")
        c.addOutlineEntry(page_label, f"img_{dr.image_upload.id}", level=1)

        y = H - MARGIN
        c.setFont("SimSun-Bold", 14)
        c.drawString(MARGIN, y, page_label)
        y -= 25

        # 原图
        orig_path = dr.image_upload.image.path
        # if os.path.exists(orig_path):
        #     c.drawImage(ImageReader(orig_path), MARGIN, y-280, width=220, height=220, preserveAspectRatio=True)
        # orig_path = dr.image_upload.image.path
        if os.path.exists(orig_path):
            # 调整原图的位置，确保与其他部分内容不重叠
            c.drawImage(ImageReader(orig_path), MARGIN, y - 100, width=100, height=100, preserveAspectRatio=True)
            # 更新 y 坐标，确保图像与后续内容的间距
            y -= 100  # 图片高度 + 适当的间距
        # 总体结论
        c.setFont("SimSun", 11)
        c.drawString(MARGIN, y - 20, f"判定：{'造假' if dr.is_fake else '真实'}")
        c.drawString(MARGIN, y - 45, f"造假概率：{dr.confidence_score:.2f}")
        y -= 70

        # LLM 结果
        if task.if_use_llm:
            y -= 10
            c.setFont("SimSun-Bold", 11)
            c.drawString(MARGIN, y, "大语言模型分析：")
            y -= 18
            y = _draw_multiline(c, MARGIN + 15, y, dr.llm_judgment or "无", max_chars=50)
            y -= 110
            if dr.llm_image and os.path.exists(dr.llm_image.path):
                c.drawImage(ImageReader(dr.llm_image.path), MARGIN + 90, y, width=100, height=100,
                            preserveAspectRatio=True)
            y -= 10

        # ELA 与 EXIF
        if dr.ela_image and os.path.exists(dr.ela_image.path):
            c.drawString(MARGIN, y, "ELA 可视化：")
            c.drawImage(ImageReader(dr.ela_image.path), MARGIN + 90, y - 100, width=100, height=100,
                        preserveAspectRatio=True)
            y -= 10
        exif_txt = f"EXIF：Photoshop 痕迹 [{'有' if dr.exif_photoshop else '无'}]   时间修改 [{'有' if dr.exif_time_modified else '无'}]"
        c.drawString(MARGIN, y - 110, exif_txt)
        y -= 130

        # 子方法
        c.setFont("SimSun-Bold", 11)
        c.drawString(MARGIN, y, "深度学习检测方法：")
        y -= 20
        for sub in dr.sub_results.all():
            y = _check_and_create_new_page(c, y, H, MARGIN)  # 调用检查函数
            c.setFont("SimSun", 10)
            c.drawString(MARGIN + 10, y, f"{sub.method}  造假概率：{sub.probability:.2f}")
            if sub.mask_image and os.path.exists(sub.mask_image.path):
                c.drawImage(ImageReader(sub.mask_image.path), MARGIN + 220, y - 40, width=60, height=60,
                            preserveAspectRatio=True)
            y -= 70

        c.showPage()

    # ─────────────────────────── 保存 ──────────────────────────
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


from ..models import ManualReview, ImageReview


def generate_manual_review_report(review: ManualReview) -> str:
    """
    生成人工审核 PDF 报告，返回相对路径，并写入 review.report_file
    """
    # 生成路径
    rel_path = f"reports/manual_review_{review.id}_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    # ─────────────────────── 封面页 ──────────────────────────
    c.bookmarkPage("cover")
    c.addOutlineEntry("人工审核概览", "cover", level=0)

    y = H - MARGIN - 20
    c.setFont("SimSun-Bold", 30)
    c.drawCentredString(W / 2, y, '“听泉鉴图”人工审核报告')
    y -= 60

    c.setFont("SimSun", 18)
    c.drawString(MARGIN, y, f"审核编号：{review.id}")
    y -= 30
    # 获取关联的任务名称（通过 DetectionTask）
    task_name = "无"
    if review.review_request and review.review_request.detection_result:
        detection_task = review.review_request.detection_result.detection_task
        if detection_task and detection_task.task_name:
            task_name = detection_task.task_name

    c.drawString(MARGIN, y, f"关联任务名称：{task_name}")

    y -= 30
    c.drawString(MARGIN, y, f"提交用户：{review.reviewer.username}")
    y -= 30

    start_time = timezone.localtime(review.review_time).strftime("%Y-%m-%d %H:%M")
    end_time = review.review_request and review.review_request.review_end_time
    finish_time = end_time and timezone.localtime(end_time).strftime("%Y-%m-%d %H:%M") or '尚未完成'

    c.drawString(MARGIN, y, f"开始时间：{start_time}")
    y -= 30
    c.drawString(MARGIN, y, f"结束时间：{finish_time}")
    y -= 30

    # 审核者列表
    # 因为 ManualReview 只有一个 reviewer 字段
    if review.reviewer:
        reviewer_names = review.reviewer.username
    else:
        reviewer_names = "未指定"

    c.drawString(MARGIN, y, f"审核人员：{reviewer_names}")
    y -= 50

    # 审核图片列表
    image_ids = ", ".join(str(img.id) for img in review.imgs.all())
    c.setFont("SimSun-Bold", 14)
    c.drawString(MARGIN, y, "审核图像列表：")
    y -= 20
    c.setFont("SimSun", 12)
    for img in review.imgs.all():
        y = _draw_multiline(c, MARGIN + 10, y, f"图片 {img.id} —— 路径：{img.image.name}", max_chars=90)
        y -= 10
        if y < MARGIN + 50:
            c.showPage()
            y = H - MARGIN
    y -= 20

    # ─────────────────────── 每张图片审核详情 ──────────────────────────
    for img_review in review.img_reviews.all():
        image_upload = img_review.img
        page_label = f"图片 {image_upload.id} 的人工审核"
        c.bookmarkPage(f"manual_img_{image_upload.id}")
        c.addOutlineEntry(page_label, f"manual_img_{image_upload.id}", level=1)

        c.setFont("SimSun-Bold", 14)
        c.drawString(MARGIN, y, page_label)
        y -= 20

        # 图像预览
        image_path = image_upload.image.path
        if os.path.exists(image_path):
            c.drawImage(ImageReader(image_path), MARGIN, y - 120, width=120, height=120, preserveAspectRatio=True)

        # 审核结果
        c.setFont("SimSun", 12)
        y -= 140
        result_text = "判定为假图" if img_review.result else "判定为真图"
        c.drawString(MARGIN, y, f"最终判定：{result_text}")
        y -= 20
        c.drawString(MARGIN, y, f"审核时间：{timezone.localtime(img_review.review_time):%Y-%m-%d %H:%M}")
        y -= 20

        # 各个评分项与理由
        c.setFont("SimSun-Bold", 12)
        c.drawString(MARGIN, y, "各维度评分与理由：")
        y -= 20
        c.setFont("SimSun", 12)

        methods = {
            1: ("Method-1", img_review.score1, img_review.reason1),
            2: ("Method-2", img_review.score2, img_review.reason2),
            3: ("Method-3", img_review.score3, img_review.reason3),
            4: ("Method-4", img_review.score4, img_review.reason4),
            5: ("Method-5", img_review.score5, img_review.reason5),
            6: ("Method-6", img_review.score6, img_review.reason6),
            7: ("Method-7", img_review.score7, img_review.reason7),
        }

        for method_id, (method_name, score, reason) in methods.items():
            y = _draw_multiline(c, MARGIN + 10, y, f"{method_name}：得分 {score}, 理由：“{reason or '无'}”",
                                max_chars=80, font='SimSun', size=11)
            y -= 10
            if y < MARGIN + 50:
                c.showPage()
                y = H - MARGIN

        # JSON 格式的点集
        points_data = {}
        try:
            points_data = json.loads(img_review.points1) if img_review.points1 else []
        except Exception:
            pass
        c.setFont("SimSun", 10)
        y -= 10
        c.drawString(MARGIN, y, "点集数据示例（Method-1）:")
        y -= 20
        sample_points = str(points_data)[:80] + ('...' if len(str(points_data)) > 80 else '')
        y = _draw_multiline(c, MARGIN + 10, y, sample_points, max_chars=80, font='SimSun', size=10)
        y -= 30

        if y < MARGIN + 50:
            c.showPage()
            y = H - MARGIN

        c.showPage()

    # ─────────────────────── 保存文件 ──────────────────────────
    c.save()
    review.report_file = rel_path
    review.save(update_fields=["report_file"])
    return rel_path

# # utils/report_generator.py
# import os, textwrap, json
# from datetime import datetime
# from django.conf import settings
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.utils import ImageReader
# from ..models import DetectionTask, DetectionResult, SubDetectionResult
# from django.utils import timezone
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
#
# pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))  # 中文字体
# pdfmetrics.registerFont(TTFont('SimSun-Bold', 'SimSun-Bold.ttf'))  # 中文加粗字体
#
#
# def _draw_multiline(c, x, y, text, max_chars=90, leading=12):
#     """把长文本自动换行绘到 PDF"""
#     for line in textwrap.wrap(text, width=max_chars):
#         c.drawString(x, y, line)
#         y -= leading
#     return y
#
#
# def generate_detection_task_report(task: DetectionTask) -> str:
#     """
#     生成任务 PDF，返回相对路径（保存到 task.report_file）
#     """
#     # 保存到 MEDIA_ROOT/reports/task_<id>_report.pdf
#     rel_path = f"reports/task_{task.id}_report.pdf"
#     abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
#     os.makedirs(os.path.dirname(abs_path), exist_ok=True)
#
#     c = canvas.Canvas(abs_path, pagesize=A4)
#     W, H = A4
#     MARGIN = 40
#     y = H - MARGIN
#
#     # ─── 任务标题 ─────────────────────────────────────────────
#     c.setFont("Helvetica-Bold", 18)
#     c.drawString(MARGIN, y, f"Detection Report  (Task #{task.id})")
#     c.setFont("Helvetica", 10)
#     y -= 20
#     c.drawString(MARGIN, y, f"User: {task.user.username}    Created: {timezone.localtime(task.upload_time):%Y-%m-%d %H:%M}")
#     y -= 25
#
#     # ─── 遍历每张图 ──────────────────────────────────────────
#     for dr in task.detection_results.select_related("image_upload").prefetch_related("sub_results"):
#         if y < 250:                # 简单分页
#             c.showPage()
#             y = H - MARGIN
#
#         # 1) 总结行
#         c.setFont("Helvetica-Bold", 12)
#         c.drawString(MARGIN, y, f"Image #{dr.image_upload.id}")
#         y -= 15
#         c.setFont("Helvetica", 10)
#         c.drawString(MARGIN, y, f"Overall fake: {dr.is_fake}      Confidence: {dr.confidence_score:.2f}")
#         y -= 15
#
#         # 2) LLM 判断S
#         if dr.llm_judgment:
#             c.setFont("SimSun", 9)
#             y = _draw_multiline(c, MARGIN, y, f"大模型检测结果：{dr.llm_judgment}", max_chars=50, leading=12)
#             # y = _draw_multiline(c, MARGIN, y, f"LLM judgment: {dr.llm_judgment}")
#
#         # 3) EXIF & ELA
#         c.setFont("Helvetica", 10)
#         exif_str = f"EXIF  PhotoshopEdited: {dr.exif_photoshop} | TimeModified: {dr.exif_time_modified}"
#         c.drawString(MARGIN, y, exif_str)
#         y -= 15
#         if dr.ela_image:
#             ela_path = os.path.join(settings.MEDIA_ROOT, dr.ela_image.name)
#             if os.path.exists(ela_path):
#                 c.drawImage(ImageReader(ela_path), MARGIN, y-120, width=120, height=120, preserveAspectRatio=True)
#                 c.drawString(MARGIN, y-130, "ELA mask")
#         y -= 140
#
#         # 4) 子检测方法
#         c.setFont("Helvetica-Bold", 10)
#         c.drawString(MARGIN, y, "Sub-method results:")
#         y -= 15
#         for sub in dr.sub_results.all():
#             c.setFont("Helvetica", 9)
#             c.drawString(MARGIN+5, y, f"{sub.method}:  {sub.probability:.2f}")
#             if sub.mask_image:
#                 mask_path = os.path.join(settings.MEDIA_ROOT, sub.mask_image.name)
#                 if os.path.exists(mask_path):
#                     c.drawImage(ImageReader(mask_path), MARGIN+150, y-50, width=80, height=80, preserveAspectRatio=True)
#             y -= 100
#
#         y -= 10  # 间距
#
#     c.save()
#     task.report_file = rel_path
#     task.save(update_fields=["report_file"])
#     return rel_path
