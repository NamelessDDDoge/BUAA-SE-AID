"""core/tests 全局夹具入口。

骨架阶段先只声明常用 fixture 的 import 桥接，具体实现等后续 PR 在
`core/tests/fixtures/` 下补齐。

迁移建议：原 `core/tests/test_image_detection_flow.py` 中的
`build_test_image()`、`unittest.mock.patch(local_inference_client.*)`
模式应抽到 `fixtures/images.py` 与本文件，避免在多个测试间复制粘贴。
"""
from __future__ import annotations

import pytest


@pytest.fixture
def api_client():
    """REST framework APIClient 实例。

    具体实现等用户/权限夹具补齐后再启用。
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def isolated_media(settings, tmp_path):
    """每个测试独立的 MEDIA_ROOT，防止 tmp-test-media 之类的目录污染。"""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    return settings.MEDIA_ROOT
