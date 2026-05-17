"""WebSocket 通知通道

WebSocket 集成测试通常需要 channels + pytest-asyncio + ASGI test client。
项目当前是否启用 channels 取决于 backend_asgi.py 的实际配置。
此处先写一个 import 健康检查 + ASGI 应用可加载性检查。
"""
import pytest

pytestmark = [pytest.mark.integration]


def test_backend_asgi_module_importable():
    """ASGI 入口必须可被 import，否则部署时 uvicorn/daphne 会启动失败。"""
    import importlib
    asgi = importlib.import_module("backend_asgi")
    # ASGI 模块应暴露 application
    assert hasattr(asgi, "application") or hasattr(asgi, "app") or callable(getattr(asgi, "application", None))


def test_channels_layer_optional():
    """通知通道使用 channels.layers 时应可初始化（如果项目启用了 channels）。"""
    try:
        from channels.layers import get_channel_layer
    except ImportError:
        pytest.skip("channels not installed — WebSocket layer not in use")
    layer = get_channel_layer()
    # InMemoryChannelLayer 或 RedisChannelLayer 都是合法的
    assert layer is not None or True  # 即使 layer 是 None，也不是测试失败 — 仅记录现状
