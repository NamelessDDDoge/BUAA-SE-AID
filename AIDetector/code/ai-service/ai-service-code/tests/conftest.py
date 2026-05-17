"""ai-service tests 全局夹具。

骨架阶段只声明 fixture 入口，具体实现等后续 PR 在 `fixtures/` 下补齐。
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DATA = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture
def fixture_data_dir() -> Path:
    """指向 tests/fixtures/data，迁入 data.json / img.zip 后可用。"""
    return FIXTURE_DATA


@pytest.fixture
def golden_dir() -> Path:
    """已知输入 -> 期望输出快照（容差比对用）。"""
    return Path(__file__).parent / "fixtures" / "golden"
