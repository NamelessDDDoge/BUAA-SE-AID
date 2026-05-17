"""跨子系统 E2E 共用夹具。

预期内容（后续填充）：
- start_backend_server: 在子进程中启动 Django runserver / uvicorn
- start_ai_service: 启动本地推理服务（如果改为常驻进程模式）
- playwright_browser: 启动 chromium，给前端 E2E 用
- api_client_for: 注入已登录的 token，返回 requests.Session
"""
import pytest


@pytest.fixture(scope="session")
def e2e_skeleton_placeholder():
    pytest.skip("TODO: E2E 夹具尚未实现")
