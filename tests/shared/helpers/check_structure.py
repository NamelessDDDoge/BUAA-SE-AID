"""测试目录结构自检脚本。

按 plan 第 3 节列出的目录清单做存在性比对。
缺哪个目录或 __init__.py 直接退出码 != 0。
CI 中可作为第一道闸。

用法:
    python tests/shared/helpers/check_structure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ---- 期望目录清单 ----
EXPECTED_DIRS = [
    # 仓库根 tests/
    "tests/e2e/image_detection",
    "tests/e2e/paper_detection",
    "tests/e2e/peer_review_detection",
    "tests/e2e/manual_review_flow",
    "tests/e2e/organization_lifecycle",
    "tests/contract/backend_vs_ai_service",
    "tests/contract/backend_vs_frontend_user",
    "tests/contract/backend_vs_frontend_admin",
    "tests/performance",
    "tests/smoke",
    "tests/shared/fixtures/images/real",
    "tests/shared/fixtures/images/fake",
    "tests/shared/fixtures/images/large",
    "tests/shared/fixtures/images/exif_modified",
    "tests/shared/fixtures/papers/normal",
    "tests/shared/fixtures/papers/with_images",
    "tests/shared/fixtures/papers/malformed",
    "tests/shared/fixtures/reviews",
    "tests/shared/factories",
    "tests/shared/helpers",
    "tests/docs",
    # backend core/tests/
    "AIDetector/code/backend/backend-code/core/tests/unit/models",
    "AIDetector/code/backend/backend-code/core/tests/unit/services/capabilities/image",
    "AIDetector/code/backend/backend-code/core/tests/unit/services/capabilities/llm",
    "AIDetector/code/backend/backend-code/core/tests/unit/services/orchestrators",
    "AIDetector/code/backend/backend-code/core/tests/unit/views",
    "AIDetector/code/backend/backend-code/core/tests/unit/utils",
    "AIDetector/code/backend/backend-code/core/tests/unit/tasks",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/auth",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/organization",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/detection",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/review",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/admin",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/llm",
    "AIDetector/code/backend/backend-code/core/tests/integration/api/notify",
    "AIDetector/code/backend/backend-code/core/tests/integration/db",
    "AIDetector/code/backend/backend-code/core/tests/integration/websocket",
    "AIDetector/code/backend/backend-code/core/tests/integration/permissions",
    "AIDetector/code/backend/backend-code/core/tests/integration/report_generation",
    "AIDetector/code/backend/backend-code/core/tests/fixtures/data",
    # ai-service tests/
    "AIDetector/code/ai-service/ai-service-code/tests/unit/config",
    "AIDetector/code/ai-service/ai-service-code/tests/unit/method/llm",
    "AIDetector/code/ai-service/ai-service-code/tests/unit/method/urn",
    "AIDetector/code/ai-service/ai-service-code/tests/unit/pipeline",
    "AIDetector/code/ai-service/ai-service-code/tests/integration",
    "AIDetector/code/ai-service/ai-service-code/tests/fixtures/data",
    "AIDetector/code/ai-service/ai-service-code/tests/fixtures/golden",
    # ai-training tests/
    "AIDetector/code/ai-training/ai-training-code/tests/unit/URN",
    "AIDetector/code/ai-training/ai-training-code/tests/integration",
    "AIDetector/code/ai-training/ai-training-code/tests/fixtures",
    # frontend-user tests/
    "AIDetector/code/frontend/frontend-user/tests/unit/stores",
    "AIDetector/code/frontend/frontend-user/tests/unit/api",
    "AIDetector/code/frontend/frontend-user/tests/unit/components",
    "AIDetector/code/frontend/frontend-user/tests/unit/composables",
    "AIDetector/code/frontend/frontend-user/tests/integration/pages",
    "AIDetector/code/frontend/frontend-user/tests/integration/features",
    "AIDetector/code/frontend/frontend-user/tests/e2e",
    "AIDetector/code/frontend/frontend-user/tests/fixtures",
    # frontend-admin tests/
    "AIDetector/code/frontend/frontend-admin/tests/unit/stores",
    "AIDetector/code/frontend/frontend-admin/tests/unit/api",
    "AIDetector/code/frontend/frontend-admin/tests/unit/components",
    "AIDetector/code/frontend/frontend-admin/tests/integration/pages",
    "AIDetector/code/frontend/frontend-admin/tests/e2e",
    "AIDetector/code/frontend/frontend-admin/tests/fixtures",
]

# ---- 期望关键文件 ----
EXPECTED_FILES = [
    "tests/pyproject.toml",
    "tests/docs/README.md",
    "tests/docs/test_matrix.md",
    "tests/docs/coverage_policy.md",
    "tests/e2e/conftest.py",
    "AIDetector/code/backend/backend-code/core/tests/conftest.py",
    "AIDetector/code/backend/backend-code/core/tests/pytest.ini",
    "AIDetector/code/backend/backend-code/core/tests/factories.py",
    "AIDetector/code/ai-service/ai-service-code/tests/conftest.py",
    "AIDetector/code/ai-service/ai-service-code/tests/pytest.ini",
    "AIDetector/code/ai-training/ai-training-code/tests/conftest.py",
    "AIDetector/code/frontend/frontend-user/tests/README.md",
    "AIDetector/code/frontend/frontend-admin/tests/README.md",
]


def main() -> int:
    missing_dirs = [d for d in EXPECTED_DIRS if not (ROOT / d).is_dir()]
    missing_files = [f for f in EXPECTED_FILES if not (ROOT / f).is_file()]

    if missing_dirs:
        print(f"[FAIL] {len(missing_dirs)} missing dir(s):")
        for d in missing_dirs:
            print(f"  - {d}")
    if missing_files:
        print(f"[FAIL] {len(missing_files)} missing file(s):")
        for f in missing_files:
            print(f"  - {f}")

    if not missing_dirs and not missing_files:
        print(f"[OK] structure check passed ({len(EXPECTED_DIRS)} dirs, {len(EXPECTED_FILES)} files)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
