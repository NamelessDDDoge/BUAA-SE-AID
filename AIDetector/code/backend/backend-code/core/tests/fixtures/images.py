"""图像测试夹具。

提炼自迁入的 `integration/api/detection/test_image_detection_flow.py`，
作为各 image 相关测试共用入口。
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile


def build_test_image(
    name: str = "test.png",
    color: tuple[int, int, int] = (255, 0, 0),
    size: tuple[int, int] = (32, 32),
) -> SimpleUploadedFile:
    """构造一张极小的 PNG，可直接喂给 ImageField。"""
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
