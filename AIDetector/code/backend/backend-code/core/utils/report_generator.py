# utils/report_generator.py
import os, re, textwrap, json, unicodedata
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

from ..models import DetectionTask, DetectionResult, SubDetectionResult
from ..constants import APP_NAME
from .task_result_store import get_paper_task_results_payload, get_review_task_results_payload

# ─── 字体注册（宋体） ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
REPORT_FONT_NAME = 'SimSun'
REPORT_FONT_BOLD_NAME = 'SimSun-Bold'


def _find_first_existing_path(candidates):
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _register_report_fonts():
    global REPORT_FONT_NAME, REPORT_FONT_BOLD_NAME
    # Use ReportLab's built-in CID font so Chinese glyphs are rendered consistently
    # across PDF viewers without depending on local TrueType collection handling.
    fallback_font_name = 'STSong-Light'
    if fallback_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(fallback_font_name))
    REPORT_FONT_NAME = fallback_font_name
    REPORT_FONT_BOLD_NAME = fallback_font_name


_register_report_fonts()


# ─── 工具函数：自动换行绘制 ───────────────────────────────
def _draw_multiline(c, x, y, text, max_chars=48, leading=14, font=REPORT_FONT_NAME, size=9):
    c.setFont(font, size)
    for line in _wrap_report_text(text, font=font, size=size, max_chars=max_chars):
        c.drawString(x, y, line)
        y -= leading
    return y


def _clean_report_text(value):
    text = _stringify_report_value(value)
    text = text.replace("\ufeff", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return text.strip()


def _wrap_report_text(text, *, font=REPORT_FONT_NAME, size=10, max_chars=None, max_width=None):
    normalized_text = _clean_report_text(text)
    if not normalized_text:
        return ["-"]
    if max_chars is None:
        if max_width is None:
            max_chars = 48
        else:
            max_chars = max(12, int(max_width / max(size * 0.9, 1)))

    def char_units(char):
        if char in " \t":
            return 0.35
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            return 1.0
        if char.isascii():
            return 0.55
        return 0.9

    lines = []
    for paragraph in str(normalized_text).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        current_units = 0.0
        for char in paragraph:
            unit_cost = char_units(char)
            if current and current_units + unit_cost > max_chars:
                lines.append(current.rstrip())
                current = char.lstrip()
                current_units = unit_cost
            else:
                current += char
                current_units += unit_cost
        if current:
            lines.append(current.rstrip())
    return lines or ["-"]


def _draw_wrapped_value(c, x, y, text, *, width, font=REPORT_FONT_NAME, size=9, leading=12, color=None, max_lines=None):
    c.setFont(font, size)
    if color is not None:
        _set_fill(c, color)
    lines = _wrap_report_text(text, font=font, size=size, max_width=width)
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last_line = lines[-1].rstrip()
        lines[-1] = last_line[:-1] + "…" if last_line else "…"
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


REPORT_FIELD_LABELS = {
    "paragraph_index": "段落编号",
    "review_paragraph_index": "评审段落编号",
    "paper_paragraph_index": "论文段落编号",
    "image_id": "图片编号",
    "page_number": "页码",
    "label": "判定",
    "status": "状态",
    "probability": "概率",
    "confidence_score": "置信度",
    "ai_verdict": "AI 判定",
    "forgery_reason": "判定原因",
    "explanation": "说明",
    "reason": "原因",
    "text": "文本",
    "review_text": "Review 文本",
    "reference": "参考文献",
    "reference_index": "参考编号",
    "exists": "是否存在",
    "is_relevant": "是否相关",
    "authenticity_score": "真实性评分",
    "authenticity_label": "真实性等级",
    "authenticity_reason": "真实性说明",
    "overlap_terms": "重合术语",
    "template_like_level": "模板化倾向",
    "wrongness_level": "内容错误风险",
    "relevance_score": "相关度评分",
    "relevance_level": "相关度等级",
    "key_findings": "关键发现",
    "suggestions": "建议",
    "summary": "总结",
    "evidence": "证据摘要",
    "is_fake": "是否造假",
    "method": "方法",
}


def _label_for_report_field(key):
    return REPORT_FIELD_LABELS.get(key, str(key))


MAX_CONTENT_HEIGHT = 40

REPORT_THEME = {
    "paper": {
        "primary": colors.HexColor("#1E3A8A"),
        "secondary": colors.HexColor("#2563EB"),
        "accent": colors.HexColor("#38BDF8"),
        "soft": colors.HexColor("#EFF6FF"),
        "soft_alt": colors.HexColor("#DBEAFE"),
        "border": colors.HexColor("#BFDBFE"),
        "text": colors.HexColor("#0F172A"),
        "muted": colors.HexColor("#475569"),
        "success": colors.HexColor("#0F766E"),
        "warning": colors.HexColor("#B45309"),
        "danger": colors.HexColor("#B91C1C"),
        "title": "论文检测报告 / Paper Detection Report",
        "subtitle": "从段落 AIGC、参考文献真实性和整体风险三个层面进行综合鉴伪。",
    },
    "review": {
        "primary": colors.HexColor("#7C2D12"),
        "secondary": colors.HexColor("#EA580C"),
        "accent": colors.HexColor("#FB923C"),
        "soft": colors.HexColor("#FFF7ED"),
        "soft_alt": colors.HexColor("#FFEDD5"),
        "border": colors.HexColor("#FED7AA"),
        "text": colors.HexColor("#1C1917"),
        "muted": colors.HexColor("#57534E"),
        "success": colors.HexColor("#166534"),
        "warning": colors.HexColor("#9A3412"),
        "danger": colors.HexColor("#C2410C"),
        "title": "同行评审检测报告 / Review Detection Report",
        "subtitle": "从模板化倾向、内容错误风险和与论文相关度三个维度评估 Review 质量。",
    },
    "image": {
        "primary": colors.HexColor("#166534"),
        "secondary": colors.HexColor("#16A34A"),
        "accent": colors.HexColor("#4ADE80"),
        "soft": colors.HexColor("#F0FDF4"),
        "soft_alt": colors.HexColor("#DCFCE7"),
        "border": colors.HexColor("#BBF7D0"),
        "text": colors.HexColor("#052E16"),
        "muted": colors.HexColor("#4B5563"),
        "success": colors.HexColor("#166534"),
        "warning": colors.HexColor("#B45309"),
        "danger": colors.HexColor("#B91C1C"),
        "title": "图像鉴伪检测报告 / Image Forensic Report",
        "subtitle": "从模型判定、EXIF 线索与辅助可视化角度评估图像真实性。",
    },
}


def _get_theme(report_type):
    return REPORT_THEME.get(report_type, REPORT_THEME["paper"])


def _safe_color(value, default):
    if value is None:
        return default
    if isinstance(value, colors.Color):
        return value
    return colors.HexColor(str(value))


def _set_fill(c, color):
    c.setFillColor(_safe_color(color, colors.black))


def _set_stroke(c, color):
    c.setStrokeColor(_safe_color(color, colors.black))


def _draw_round_box(c, x, y_top, width, height, *, fill=None, stroke=None, radius=10, stroke_width=1):
    if fill is not None:
        _set_fill(c, fill)
    if stroke is not None:
        _set_stroke(c, stroke)
        c.setLineWidth(stroke_width)
    c.roundRect(x, y_top - height, width, height, radius, fill=1 if fill is not None else 0, stroke=1 if stroke is not None else 0)


def _measure_text_width(text, font=REPORT_FONT_NAME, size=10):
    return stringWidth(str(text), font, size)


def _draw_badge(c, x, y, text, *, fill, text_color=colors.white, font=None, size=9, padding_x=8, padding_y=4):
    badge_font = font or REPORT_FONT_BOLD_NAME
    badge_text = _stringify_report_value(text)
    badge_width = _measure_text_width(badge_text, badge_font, size) + padding_x * 2
    badge_height = size + padding_y * 2
    _draw_round_box(c, x, y, badge_width, badge_height, fill=fill, stroke=fill, radius=badge_height / 2, stroke_width=0.8)
    c.setFont(badge_font, size)
    _set_fill(c, text_color)
    c.drawString(x + padding_x, y - badge_height + padding_y + 1, badge_text)
    return badge_width


def _draw_rule(c, x, y, width, *, color, thickness=1):
    _set_stroke(c, color)
    c.setLineWidth(thickness)
    c.line(x, y, x + width, y)


def _draw_hero_page(c, *, task, width, height, margin, metadata_lines, theme, report_kind_label):
    c.setFillColor(theme["soft"])
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(theme["primary"])
    c.rect(0, height - 122, width, 122, fill=1, stroke=0)
    c.setFillColor(theme["accent"])
    c.circle(width - 78, height - 66, 34, fill=1, stroke=0)
    c.setFillColor(theme["soft_alt"])
    c.circle(width - 40, height - 105, 16, fill=1, stroke=0)

    c.setFont(REPORT_FONT_BOLD_NAME, 10)
    _set_fill(c, colors.white)
    c.drawString(margin, height - 42, report_kind_label)

    y = height - 160
    c.setFont(REPORT_FONT_BOLD_NAME, 26)
    _set_fill(c, theme["text"])
    c.drawString(margin, y, theme["title"])
    y -= 22
    c.setFont(REPORT_FONT_NAME, 11)
    _set_fill(c, theme["muted"])
    y = _draw_multiline(c, margin, y, theme["subtitle"], max_chars=40, leading=15, size=11)

    y -= 18
    _draw_rule(c, margin, y, width - margin * 2, color=theme["border"], thickness=1.2)
    y -= 30

    c.setFont(REPORT_FONT_BOLD_NAME, 14)
    _set_fill(c, theme["primary"])
    c.drawString(margin, y, "任务概览")
    y -= 22

    for line in metadata_lines:
        _draw_report_text_card(c, y, line, width=width - margin * 2, height=24, theme=theme, size=10)
        y -= 30

    return y


def _draw_report_text_card(c, y_top, text, *, width, height=None, theme, size=10, left_padding=12):
    normalized_text = _clean_report_text(text)
    estimated_lines = max(len(_wrap_report_text(normalized_text, font=REPORT_FONT_NAME, size=size, max_width=width - left_padding * 2)), 1)
    card_height = height or max(24, estimated_lines * 14 + 14)
    _draw_round_box(c, 40, y_top, width, card_height, fill=theme["soft"], stroke=theme["border"], radius=10)
    _draw_wrapped_value(
        c,
        40 + left_padding,
        y_top - 16,
        normalized_text,
        width=width - left_padding * 2,
        font=REPORT_FONT_NAME,
        size=size,
        leading=13,
        color=theme["text"],
    )
    return y_top - card_height - 8


def _draw_summary_grid(c, y, *, width, theme, items, columns=2):
    gap = 10
    side_margin = 56
    card_width = (width - side_margin * 2 - gap * (columns - 1)) / columns
    for start in range(0, len(items), columns):
        row_items = items[start:start + columns]
        current_x = side_margin
        row_top = y
        row_heights = []
        for item in row_items:
            value = _clean_report_text(item[1])
            value_lines = _wrap_report_text(value, font=REPORT_FONT_BOLD_NAME, size=12, max_width=card_width - 24)
            row_heights.append(max(58, 18 + len(value_lines) * 14 + 8))
        row_height = max(row_heights) if row_heights else 58
        for item in row_items:
            _draw_round_box(c, current_x, row_top, card_width, row_height, fill=theme["soft_alt"], stroke=theme["border"], radius=12)
            c.setFont(REPORT_FONT_BOLD_NAME, 10)
            _set_fill(c, theme["muted"])
            label = _clean_report_text(item[0])
            value = _clean_report_text(item[1])
            c.drawString(current_x + 12, row_top - 18, label)
            _draw_wrapped_value(
                c,
                current_x + 12,
                row_top - 36,
                value,
                width=card_width - 24,
                font=REPORT_FONT_BOLD_NAME,
                size=12,
                leading=14,
                color=theme["primary"],
            )
            current_x += card_width + gap
        y -= row_height + gap
    return y


def _draw_summary_blocks(c, y, *, width, height, margin, theme, items):
    block_width = width - 80
    for label, value in items:
        rendered_value = _clean_report_text(value)
        value_lines = _wrap_report_text(rendered_value, font=REPORT_FONT_NAME, size=10, max_width=block_width - 128)
        block_height = max(40, 18 + len(value_lines) * 12 + 6)
        y = _ensure_report_space(c, y, height, margin, needed_height=block_height + 10)
        _draw_round_box(c, 40, y + 4, block_width, block_height, fill=theme["soft_alt"], stroke=theme["border"], radius=12)

        c.setFont(REPORT_FONT_BOLD_NAME, 10)
        _set_fill(c, theme["muted"])
        c.drawString(52, y + block_height - 16, f"{_clean_report_text(label)}：")

        _draw_wrapped_value(
            c,
            136,
            y + block_height - 16,
            rendered_value,
            width=block_width - 96,
            font=REPORT_FONT_NAME,
            size=10,
            leading=12,
            color=theme["primary"],
        )
        y -= block_height + 8
    return y


def _draw_section_header(c, y, *, title, theme, height, margin, subtitle=None):
    y = _ensure_report_space(c, y, height, margin, needed_height=50)
    title_offset = 6
    _draw_rule(c, margin, y - title_offset, 28, color=theme["accent"], thickness=4)
    c.setFont(REPORT_FONT_BOLD_NAME, 15)
    _set_fill(c, theme["text"])
    c.drawString(margin + 36, y - 6 - title_offset, title)
    if subtitle:
        c.setFont(REPORT_FONT_NAME, 9)
        _set_fill(c, theme["muted"])
        c.drawRightString(margin + 460, y - 6 - title_offset, subtitle)
    return y - 26 - title_offset


def _draw_key_value_block(c, y_top, label, value, *, width, theme, label_x, value_x, label_font_size=9, value_font_size=9, leading=11, max_lines=None):
    rendered_label = _clean_report_text(label)
    rendered_value = _clean_report_text(value)
    value_lines = _wrap_report_text(rendered_value, font=REPORT_FONT_NAME, size=value_font_size, max_width=width - (value_x - label_x))
    if max_lines is not None and len(value_lines) > max_lines:
        value_lines = value_lines[:max_lines]
    block_height = max(28, 16 + len(value_lines) * leading + 4)

    c.setFont(REPORT_FONT_BOLD_NAME, label_font_size)
    _set_fill(c, theme["muted"])
    c.drawString(label_x, y_top - 12, f"{rendered_label}：")

    _draw_wrapped_value(
        c,
        value_x,
        y_top - 12,
        rendered_value,
        width=width - (value_x - label_x),
        font=REPORT_FONT_NAME,
        size=value_font_size,
        leading=leading,
        color=theme["text"],
        max_lines=max_lines,
    )
    _draw_rule(c, label_x - 2, y_top - block_height + 4, width, color=theme["border"], thickness=0.5)
    return block_height


def _draw_metric_badges(c, y, items, *, theme):
    x = 40
    baseline = y
    for label, value, kind in items:  # Iterate through badge items
        badge_text = f"{label} {value}"
        color = theme["primary"]
        if kind == "success":
            color = theme["success"]
        elif kind == "warning":
            color = theme["warning"]
        elif kind == "danger":
            color = theme["danger"]
        width = _draw_badge(c, x, baseline, badge_text, fill=color, size=9)
        x += width + 8
    return baseline - 18


def _draw_image_preview_card(c, y, *, image_path, title, theme, width=515, height=150, margin=40, image_size=120):
    y = _ensure_report_space(c, y, A4[1], margin, needed_height=height + 6)
    _draw_round_box(c, margin, y, width, height, fill=theme["soft"], stroke=theme["border"], radius=12)
    c.setFont(REPORT_FONT_BOLD_NAME, 10)
    _set_fill(c, theme["muted"])
    c.drawString(margin + 12, y - 16, title)

    if image_path and os.path.exists(image_path):
        img_x = margin + 12
        img_top = y - 30
        img_y = img_top - image_size
        c.drawImage(ImageReader(image_path), img_x, img_y, width=image_size, height=image_size, preserveAspectRatio=True)
    else:
        # Leave the preview area blank when no image is available.
        pass
    return y - height - 8


def _resolve_label_color(theme, value):
    text = str(value or "")
    if any(token in text for token in ("高", "严重", "异常", "假", "危险", "不相关", "低")):
        return theme["danger"]
    if any(token in text for token in ("中", "部分", "一般", "可疑")):
        return theme["warning"]
    if any(token in text for token in ("低风险", "正常", "真实", "相关", "通过", "较低", "高相关", "较高")):
        return theme["success"]
    return theme["primary"]


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
    theme = _get_theme("image")
    c, rel_path, width, height, margin = _create_report_canvas(task)

    c.bookmarkPage("cover")
    c.addOutlineEntry("任务概览", "cover", level=0)
    _draw_report_title_page(
        c,
        title=theme["title"],
        task=task,
        width=width,
        height=height,
        margin=margin,
        metadata_lines=[
            f"任务编号：{task.id}",
            f"任务名称：{task.task_name}",
            f"用户：{task.user.username}",
            f"创建时间：{timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M')}",
            f"完成时间：{timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M') if task.completion_time else '-'}",
            f"cmd_block_size：{task.cmd_block_size}",
            f"urn_k：{task.urn_k}",
            f"使用大语言模型：{'是' if task.if_use_llm else '否'}",
        ],
        theme=theme,
        report_kind_label="IMAGE FORENSIC REPORT",
    )

    # ─────────────────────── 每张图片一页 ──────────────────────
    for dr in task.detection_results.select_related("image_upload").prefetch_related("sub_results").order_by("id"):
        page_label = f"图片 {dr.image_upload.id}"
        c.bookmarkPage(f"img_{dr.image_upload.id}")
        c.addOutlineEntry(page_label, f"img_{dr.image_upload.id}", level=1)

        y = height - margin
        y = _draw_report_section_title(c, y, title=page_label, height=height, margin=margin, theme=theme, subtitle="图像级综合判定")

        orig_path = dr.image_upload.image.path if dr.image_upload and dr.image_upload.image else ""
        y = _draw_image_preview_card(c, y, image_path=orig_path, title="原始图像预览", theme=theme, margin=margin)
        y = _draw_report_items(
            c,
            y,
            [
                {
                    "label": "造假" if dr.is_fake else "真实",
                    "confidence_score": dr.confidence_score,
                    "status": dr.status,
                }
            ],
            height=height,
            margin=margin,
            theme=theme,
        )

        if task.if_use_llm:
            y = _draw_report_section_title(c, y, title="大语言模型分析", height=height, margin=margin, theme=theme)
            y = _draw_report_items(
                c,
                y,
                [{"explanation": dr.llm_judgment or "无"}],
                height=height,
                margin=margin,
                theme=theme,
                max_lines_overrides={"explanation": 8},
            )
            llm_image_path = dr.llm_image.path if dr.llm_image else ""
            if llm_image_path:
                y = _draw_image_preview_card(c, y, image_path=llm_image_path, title="LLM 可视化", theme=theme, margin=margin)

        if dr.ela_image and os.path.exists(dr.ela_image.path):
            y = _draw_report_section_title(c, y, title="ELA 可视化", height=height, margin=margin, theme=theme)
            y = _draw_image_preview_card(c, y, image_path=dr.ela_image.path, title="ELA 结果", theme=theme, margin=margin)

        exif_txt = f"EXIF：Photoshop 痕迹 [{'有' if dr.exif_photoshop else '无'}]   时间修改 [{'有' if dr.exif_time_modified else '无'}]"
        y = _draw_report_items(
            c,
            y,
            [{"explanation": exif_txt}],
            height=height,
            margin=margin,
            theme=theme,
            max_lines_overrides={"explanation": 4},
        )

        if dr.sub_results.exists():
            y = _draw_report_section_title(c, y, title="深度学习检测方法", height=height, margin=margin, theme=theme)
            y = _draw_report_items(
                c,
                y,
                [
                    {"method": sub.method, "probability": sub.probability}
                    for sub in dr.sub_results.all()
                ],
                height=height,
                margin=margin,
                theme=theme,
            )

        c.showPage()

    # ─────────────────────────── 保存 ──────────────────────────
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


def generate_task_report(task: DetectionTask) -> str:
    if task.task_type == "paper":
        return generate_paper_detection_task_report(task)
    if task.task_type == "review":
        return generate_review_detection_task_report(task)
    return generate_detection_task_report(task)


def ensure_task_report_file(task: DetectionTask, *, force: bool = False) -> str:
    report_name = getattr(task.report_file, "name", "") or ""
    abs_path = os.path.join(settings.MEDIA_ROOT, report_name) if report_name else ""
    if force or not report_name or not os.path.exists(abs_path):
        return generate_task_report(task)
    return report_name


def _create_report_canvas(task: DetectionTask):
    rel_path = f"reports/task_{task.id}_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    report_canvas = canvas.Canvas(abs_path, pagesize=A4)
    width, height = A4
    margin = 40
    return report_canvas, rel_path, width, height, margin


def _ensure_report_space(c, y, height, margin, needed_height=40):
    if y - needed_height < margin:
        c.showPage()
        y = height - margin
    return y


def _draw_report_title_page(c, *, title, task, width, height, margin, metadata_lines, theme, report_kind_label):
    _draw_hero_page(
        c,
        task=task,
        width=width,
        height=height,
        margin=margin,
        metadata_lines=metadata_lines,
        theme=theme,
        report_kind_label=report_kind_label,
    )
    c.showPage()


def _draw_report_section_title(c, y, *, title, height, margin, theme, subtitle=None):
    return _draw_section_header(c, y, title=title, theme=theme, height=height, margin=margin, subtitle=subtitle)


def _draw_report_text_block(c, y, text, *, height, margin, max_chars=46, leading=14, size=10, theme=None):
    normalized_text = _clean_report_text(text)
    line_count = max(len(_wrap_report_text(normalized_text, font=REPORT_FONT_NAME, size=size, max_chars=max_chars)), 1)
    y = _ensure_report_space(c, y, height, margin, needed_height=line_count * leading + 10)
    if theme:
        block_height = max(line_count * leading + 10, 24)
        _draw_round_box(c, margin, y, 515, block_height, fill=theme["soft"], stroke=theme["border"], radius=10)
        _set_fill(c, theme["text"])
        text_y = y - 16
        _draw_multiline(c, margin + 12, text_y, normalized_text, max_chars=max_chars, leading=leading, size=size)
        return y - block_height - 8
    return _draw_multiline(c, margin + 12, y, normalized_text, max_chars=max_chars, leading=leading, size=size) - 8


def _draw_report_pairs(c, y, pairs, *, height, margin, theme):
    for label, value in pairs:
        rendered_value = _clean_report_text(value)
        badge_color = _resolve_label_color(theme, rendered_value)
        label_text = _clean_report_text(label)
        value_lines = _wrap_report_text(rendered_value, font=REPORT_FONT_NAME, size=9, max_width=360)
        block_height = max(34, 18 + len(value_lines) * 11 + 4)
        y = _ensure_report_space(c, y, height, margin, needed_height=block_height + 6)
        _draw_round_box(c, margin, y, 515, block_height, fill=theme["soft"], stroke=theme["border"], radius=10)
        c.setFont(REPORT_FONT_BOLD_NAME, 10)
        _set_fill(c, theme["muted"])
        c.drawString(margin + 12, y - 12, f"{label_text}：")
        _draw_wrapped_value(
            c,
            margin + 110,
            y - 24,
            rendered_value,
            width=515 - 122,
            font=REPORT_FONT_NAME,
            size=9,
            leading=11,
            color=badge_color,
        )
        y -= block_height + 8
    return y


def _is_effectively_empty_item(item):
    if item is None:
        return True
    if isinstance(item, str):
        return _clean_report_text(item) in {"", "-", "无"}
    if isinstance(item, dict):
        return all(_clean_report_text(value) in {"", "-", "无"} for value in item.values())
    if isinstance(item, (list, tuple, set)):
        return len(item) == 0
    return False


def _draw_report_items(c, y, items, *, height, margin, theme, start_index=1, max_lines_overrides=None):
    if items and all(_is_effectively_empty_item(item) for item in items):
        items = []
    if not items:
        card_height = 44
        y = _ensure_report_space(c, y, height, margin, needed_height=card_height + 6)
        _draw_round_box(c, margin, y, 515, card_height, fill=theme["soft"], stroke=theme["border"], radius=10)
        c.setFont(REPORT_FONT_NAME, 9)
        _set_fill(c, theme["text"])
        c.drawString(margin + 46, y - 18, "无")
        return y - card_height - 4

    value_col_x_offset = 112
    inner_width = 515 - value_col_x_offset - 12
    long_text_fields = {"text", "review_text", "reference", "summary", "evidence", "forgery_reason", "explanation", "authenticity_reason", "key_findings", "suggestions"}
    max_lines_overrides = max_lines_overrides or {}

    for index, item in enumerate(items, start=start_index):
        if isinstance(item, dict):
            content_rows = [
                (key, _label_for_report_field(key), _clean_report_text(value))
                for key, value in item.items()
            ]
            row_heights = []
            for field_key, _label, value in content_rows:
                wrap_width = inner_width - 40 if field_key in long_text_fields else inner_width
                lines = _wrap_report_text(value, font=REPORT_FONT_NAME, size=9, max_width=wrap_width)
                override_max_lines = max_lines_overrides.get(field_key)
                if override_max_lines is not None:
                    lines = lines[:override_max_lines]
                line_count = len(lines)
                if field_key in long_text_fields:
                    row_heights.append(max(44, 20 + line_count * 12 + 8))
                else:
                    row_heights.append(max(28, 16 + line_count * 11 + 4))
            card_height = max(54, 16 + sum(row_heights) + max(len(content_rows) - 1, 0) * 4)
        else:
            rendered_item = _clean_report_text(item)
            item_lines = _wrap_report_text(rendered_item, font=REPORT_FONT_NAME, size=9, max_width=460)
            card_height = max(54, 18 + len(item_lines) * 12)

        y = _ensure_report_space(c, y, height, margin, needed_height=card_height + 6)
        _draw_round_box(c, margin, y, 515, card_height, fill=theme["soft"], stroke=theme["border"], radius=10)
        _draw_badge(c, margin + 12, y - 6, f"{index}", fill=theme["primary"], size=8)
        if isinstance(item, dict):
            content_y = y - 12
            for row_index, (field_key, label, value) in enumerate(content_rows):
                row_height = row_heights[row_index]
                row_width = 515 - 54 - (40 if field_key in long_text_fields else 0)
                max_lines = None
                if field_key in max_lines_overrides:
                    max_lines = max_lines_overrides.get(field_key)
                elif field_key not in {"text", "review_text"}:
                    max_lines = 4 if field_key in long_text_fields else 2
                _draw_key_value_block(
                    c,
                    content_y,
                    label,
                    value,
                    width=row_width,
                    theme=theme,
                    label_x=margin + 46,
                    value_x=margin + 112,
                    label_font_size=9,
                    value_font_size=9,
                    leading=11,
                    max_lines=max_lines,
                )
                content_y -= row_height + 4
        else:
            _draw_wrapped_value(
                c,
                margin + 46,
                y - 14,
                rendered_item,
                width=515 - 58,
                font=REPORT_FONT_NAME,
                size=9,
                leading=11,
                color=theme["text"],
            )
        y -= card_height
        y -= 4
    return y


def _stringify_report_value(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, (int, str)):
        return str(value)
    if isinstance(value, dict):
        return ", ".join(f"{key}={_stringify_report_value(item)}" for key, item in value.items()) or "-"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_stringify_report_value(item) for item in value) or "-"
    return str(value)


def generate_paper_detection_task_report(task: DetectionTask) -> str:
    results = get_paper_task_results_payload(task)
    document = results.get("document", {})
    items = results.get("items", []) or []
    paragraph_results = results.get("paragraph_results", [])
    confirmed_ai_paragraphs = results.get("confirmed_ai_paragraphs", [])
    suspicious_paragraphs = results.get("suspicious_paragraphs", [])
    reference_results = results.get("reference_results", [])
    data_authenticity_results = results.get("data_authenticity_results", {})
    overall_evaluation = results.get("overall_evaluation", {})
    image_results = results.get("image_results", [])
    paper_file = task.resource_files.filter(resource_type="paper").first()
    theme = _get_theme("paper")

    c, rel_path, width, height, margin = _create_report_canvas(task)
    _draw_report_title_page(
        c,
        title=theme["title"],
        task=task,
        width=width,
        height=height,
        margin=margin,
        metadata_lines=[
            f"任务编号：{task.id}",
            f"任务名称：{task.task_name}",
            f"用户：{task.user.username}",
            f"源文件：{paper_file.file_name if paper_file else '-'}",
            f"创建时间：{timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M')}",
            f"完成时间：{timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M') if task.completion_time else '-'}",
        ],
        theme=theme,
        report_kind_label="IMAGE / PAPER FORENSIC REPORT",
    )

    y = height - margin
    y = _draw_report_section_title(c, y, title="文档摘要", height=height, margin=margin, theme=theme, subtitle="基础信息与检测配置")
    y = _draw_summary_grid(
        c,
        y,
        width=width,
        theme=theme,
        items=[
            ("文件名", paper_file.file_name if paper_file else "-"),
            ("段落数", _stringify_report_value(document.get("paragraph_count"))),
            ("分段数", _stringify_report_value(document.get("segment_count"))),
            ("参考文献数", _stringify_report_value(document.get("reference_count"))),
            ("启用图片检测", _stringify_report_value(document.get("image_detection_enabled"))),
            ("AI 段落数", _stringify_report_value(len(confirmed_ai_paragraphs))),
            ("总体风险", overall_evaluation.get("risk_level")),
            ("风险评分", overall_evaluation.get("risk_score")),
        ],
    )

    if len(items) > 1:
        y = _draw_report_section_title(c, y, title="批量资源总览", height=height, margin=margin, theme=theme, subtitle="任务内多篇论文处理概览")
        y = _draw_report_items(
            c,
            y,
            [
                {
                    "file_name": item.get("document", {}).get("file_name"),
                    "paragraph_count": item.get("document", {}).get("paragraph_count"),
                    "reference_count": item.get("document", {}).get("reference_count"),
                    "confirmed_ai_count": len(item.get("confirmed_ai_paragraphs") or []),
                    "suspicious_count": len(item.get("suspicious_paragraphs") or []),
                }
                for item in items
            ],
            height=height,
            margin=margin,
            theme=theme,
        )

    y = _draw_report_section_title(c, y, title="段落检测结果", height=height, margin=margin, theme=theme, subtitle="Fast-Detect 段落判定")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "paragraph_index": item.get("paragraph_index"),
                "label": item.get("label"),
                "probability": item.get("probability"),
                "ai_verdict": item.get("ai_verdict") or (item.get("details") or {}).get("ai_verdict"),
                "forgery_reason": item.get("forgery_reason") or (item.get("details") or {}).get("forgery_reason"),
                "text": item.get("text"),
            }
            for item in paragraph_results
        ],
        height=height,
        margin=margin,
        theme=theme,
        max_lines_overrides={"text": 8},
    )

    y = _draw_report_section_title(c, y, title="基本确认 AI 段落", height=height, margin=margin, theme=theme, subtitle="被系统确认的高风险段落")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "paragraph_index": item.get("paragraph_index"),
                "probability": item.get("probability"),
                "reason": item.get("reason"),
            }
            for item in confirmed_ai_paragraphs
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    y = _draw_report_section_title(c, y, title="可疑段落解释", height=height, margin=margin, theme=theme, subtitle="需要重点关注的段落说明")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "paragraph_index": item.get("paragraph_index"),
                "probability": item.get("probability"),
                "explanation": item.get("explanation"),
            }
            for item in suspicious_paragraphs
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    y = _draw_report_section_title(c, y, title="参考文献检查", height=height, margin=margin, theme=theme, subtitle="引用真实性与相关性检查")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "reference_index": item.get("reference_index"),
                "exists": item.get("exists"),
                "is_relevant": item.get("is_relevant"),
                "authenticity_score": item.get("authenticity_score"),
                "authenticity_label": item.get("authenticity_label"),
                "authenticity_reason": item.get("authenticity_reason"),
                "reference": item.get("reference"),
                "overlap_terms": item.get("overlap_terms"),
            }
            for item in reference_results
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    y = _draw_report_section_title(c, y, title="整篇论文综合评价", height=height, margin=margin, theme=theme, subtitle="综合风险与证据摘要")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "authenticity_score": overall_evaluation.get("risk_score"),
                "authenticity_label": overall_evaluation.get("risk_level"),
                "summary": overall_evaluation.get("summary"),
                "evidence": overall_evaluation.get("evidence"),
            }
        ],
        height=height,
        margin=margin,
        theme=theme,
        max_lines_overrides={"summary": 6, "evidence": 6},
    )

    y = _draw_report_section_title(c, y, title="论文图片检测", height=height, margin=margin, theme=theme, subtitle="图像级检测结果概览")
    _draw_report_items(
        c,
        y,
        [
            {
                "image_id": item.get("image_id"),
                "page_number": item.get("page_number"),
                "status": item.get("status"),
                "is_fake": item.get("is_fake"),
                "confidence_score": item.get("confidence_score"),
            }
            for item in image_results
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


def generate_review_detection_task_report(task: DetectionTask) -> str:
    results = get_review_task_results_payload(task)
    document = results.get("document", {})
    items = results.get("items", []) or []
    paragraph_results = results.get("paragraph_results", [])
    review_analysis = results.get("review_analysis_results", {}) or {}
    overall_evaluation = review_analysis.get("overall", {}) or results.get("overall_evaluation", {}) or {}
    review_analysis_paragraphs = review_analysis.get("paragraph_results", []) or results.get("relevance_results", [])
    suspicious_paragraphs = results.get("suspicious_paragraphs", [])
    theme = _get_theme("review")

    c, rel_path, width, height, margin = _create_report_canvas(task)
    _draw_report_title_page(
        c,
        title=theme["title"],
        task=task,
        width=width,
        height=height,
        margin=margin,
        metadata_lines=[
            f"任务编号：{task.id}",
            f"任务名称：{task.task_name}",
            f"用户：{task.user.username}",
            f"论文文件：{document.get('paper_file_name', '-')}",
            f"评审文件：{document.get('review_file_name', '-')}",
            f"创建时间：{timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M')}",
            f"完成时间：{timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M') if task.completion_time else '-'}",
        ],
        theme=theme,
        report_kind_label="REVIEW ANALYSIS REPORT",
    )

    y = height - margin
    y = _draw_report_section_title(c, y, title="文档摘要", height=height, margin=margin, theme=theme, subtitle="论文与 Review 的基础信息")
    y = _draw_summary_grid(
        c,
        y,
        width=width,
        theme=theme,
        items=[
            ("论文分段数", _stringify_report_value(document.get("paper_segment_count"))),
            ("评审分段数", _stringify_report_value(document.get("review_segment_count"))),
            ("评审段落数", _stringify_report_value(document.get("review_paragraph_count"))),
            ("综合结论", _stringify_report_value(overall_evaluation.get("qualification_text"))),
            ("模板化倾向", _stringify_report_value(overall_evaluation.get("template_like_level"))),
            ("内容错误风险", overall_evaluation.get("wrongness_level")),
            ("与论文相关度", overall_evaluation.get("relevance_level")),
        ],
    )

    if len(items) > 1:
        y = _draw_report_section_title(c, y, title="批量资源总览", height=height, margin=margin, theme=theme, subtitle="任务内多组论文与 Review 处理概览")
        y = _draw_report_items(
            c,
            y,
            [
                {
                    "paper_file_name": item.get("document", {}).get("paper_file_name"),
                    "review_file_name": item.get("document", {}).get("review_file_name"),
                    "review_paragraph_count": item.get("document", {}).get("review_paragraph_count"),
                    "suspicious_count": len(item.get("suspicious_paragraphs") or []),
                    "relevance_count": len(item.get("relevance_results") or []),
                }
                for item in items
            ],
            height=height,
            margin=margin,
            theme=theme,
        )

    y = _draw_report_section_title(c, y, title="Review 综合审查", height=height, margin=margin, theme=theme, subtitle="模板化、错误与相关性综合判断")
    y = _draw_report_pairs(
        c,
        y,
        [
            ("综合结论", overall_evaluation.get("qualification_text")),
            ("判定原因", overall_evaluation.get("qualification_reason")),
            ("模板化倾向", overall_evaluation.get("template_like_level")),
            ("内容错误风险", overall_evaluation.get("wrongness_level")),
            ("与论文相关度", overall_evaluation.get("relevance_level")),
            ("综合总结", overall_evaluation.get("summary")),
        ],
        height=height,
        margin=margin,
        theme=theme,
    )
    y = _draw_report_items(
        c,
        y,
        [
            {"key_findings": overall_evaluation.get("key_findings", [])},
            {"suggestions": overall_evaluation.get("suggestions", [])},
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    y = _draw_report_section_title(c, y, title="Review 段落审查", height=height, margin=margin, theme=theme, subtitle="逐段模板化与相关性分析")
    y = _draw_report_items(
        c,
        y,
        [
            {
                "review_paragraph_index": item.get("review_paragraph_index", item.get("paragraph_index")),
                "template_like_level": item.get("template_like_level") or (item.get("details") or {}).get("template_like_level"),
                "wrongness_level": item.get("wrongness_level") or (item.get("details") or {}).get("wrongness_level"),
                "relevance_score": item.get("relevance_score") or (item.get("details") or {}).get("relevance_score"),
                "relevance_level": item.get("relevance_level") or (item.get("details") or {}).get("relevance_level"),
                "explanation": item.get("explanation") or item.get("relevance_explanation") or (item.get("details") or {}).get("explanation"),
                "text": item.get("review_text") or item.get("text"),
                "paper_paragraph_index": item.get("paper_paragraph_index"),
            }
            for item in review_analysis_paragraphs
        ],
        height=height,
        margin=margin,
        theme=theme,
    )

    y = _draw_report_section_title(c, y, title="可疑段落解释", height=height, margin=margin, theme=theme, subtitle="需要重点关注的 Review 内容")
    y = _draw_report_items(c, y, suspicious_paragraphs, height=height, margin=margin, theme=theme)

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
    c.setFont(REPORT_FONT_BOLD_NAME, 30)
    c.drawCentredString(W / 2, y, f'“{APP_NAME}”人工审核报告')
    y -= 60

    c.setFont(REPORT_FONT_NAME, 18)
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
    c.setFont(REPORT_FONT_BOLD_NAME, 14)
    c.drawString(MARGIN, y, "审核图像列表：")
    y -= 20
    c.setFont(REPORT_FONT_NAME, 12)
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

        c.setFont(REPORT_FONT_BOLD_NAME, 14)
        c.drawString(MARGIN, y, page_label)
        y -= 20

        # 图像预览
        image_path = image_upload.image.path
        if os.path.exists(image_path):
            c.drawImage(ImageReader(image_path), MARGIN, y - 120, width=120, height=120, preserveAspectRatio=True)

        # 审核结果
        c.setFont(REPORT_FONT_NAME, 12)
        y -= 140
        result_text = "判定为假图" if img_review.result else "判定为真图"
        c.drawString(MARGIN, y, f"最终判定：{result_text}")
        y -= 20
        c.drawString(MARGIN, y, f"审核时间：{timezone.localtime(img_review.review_time):%Y-%m-%d %H:%M}")
        y -= 20

        # 各个评分项与理由
        c.setFont(REPORT_FONT_BOLD_NAME, 12)
        c.drawString(MARGIN, y, "各维度评分与理由：")
        y -= 20
        c.setFont(REPORT_FONT_NAME, 12)

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
                                max_chars=80, font=REPORT_FONT_NAME, size=11)
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
        c.setFont(REPORT_FONT_NAME, 10)
        y -= 10
        c.drawString(MARGIN, y, "点集数据示例（Method-1）:")
        y -= 20
        sample_points = str(points_data)[:80] + ('...' if len(str(points_data)) > 80 else '')
        y = _draw_multiline(c, MARGIN + 10, y, sample_points, max_chars=80, font=REPORT_FONT_NAME, size=10)
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
