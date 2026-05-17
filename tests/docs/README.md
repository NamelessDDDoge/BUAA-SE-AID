# BUAA-SE-AID 测试体系总览

本仓库由四个相对独立的子系统组成，测试也按子系统自治、按测试金字塔分层组织。

## 目录布局速览

```
tests/                                          # 仓库根 — 跨子系统层
├── e2e/                                        # 多服务联跑
├── contract/                                   # 前后端 / 后端-推理服务契约
├── performance/                                # 压测脚本
├── smoke/                                      # 上线冒烟
├── shared/{fixtures,factories,helpers}/        # 跨系统共用资产
└── docs/                                       # 本目录

AIDetector/code/backend/backend-code/core/tests/   # Django 后端
AIDetector/code/ai-service/ai-service-code/tests/  # 推理服务
AIDetector/code/ai-training/ai-training-code/tests/# 训练代码
AIDetector/code/frontend/frontend-user/tests/      # Vue 用户端
AIDetector/code/frontend/frontend-admin/tests/     # Vue 管理端
```

每个子系统内统一拆为 `unit/`、`integration/`、（可选）`e2e/`、`fixtures/`。

## 如何跑测试

### 后端（Django）
```pwsh
cd AIDetector/code/backend/backend-code
pytest                                          # 默认跳过 gpu/e2e/slow
pytest -m unit                                  # 只跑单测
pytest -m "integration and not slow"            # 跑集成测试（排除慢）
pytest --cov=core --cov-report=term-missing     # 带覆盖率
```

### 推理服务
```pwsh
cd AIDetector/code/ai-service/ai-service-code
pytest                                          # CPU 单测
pytest -m gpu                                   # 真跑模型（需 CUDA）
```

### 前端（Vitest + Playwright）
```pwsh
cd AIDetector/code/frontend/frontend-user
pnpm test                                       # vitest run
pnpm test:e2e                                   # playwright
```

### 跨子系统
```pwsh
cd tests
pytest contract/                                # 契约测试
pytest e2e/                                     # 真 E2E（需 docker-compose 先起服务）
```

## 如何加新测试

1. **先定位测试层**：纯函数/单类 → `unit/`，走 ORM/HTTP → `integration/`，跨多个服务 → 仓库根 `tests/e2e/`。
2. **目录镜像源码**：要测 `core/services/orchestrators/image_task_orchestrator.py`，测试放到 `core/tests/unit/services/orchestrators/test_image_task_orchestrator.py`。
3. **设计文档单元 ↔ 测试** 双向映射见 [`test_matrix.md`](test_matrix.md)。新增功能时同步更新映射表。
4. **覆盖率门槛** 见 [`coverage_policy.md`](coverage_policy.md)，PR 不允许下降。

## 设计原则（来自 `python-plan-steady-clock.md` 第 2 节）

1. 每个子系统自治，不强行做仓库级"大一统"框架
2. 测试金字塔显式分层：unit → integration → e2e
3. 目录镜像源码
4. 跨子系统测试提升到仓库根
5. fixture 集中收口，临时产物不进仓
6. 设计文档 ↔ 测试双向映射
