# 覆盖率门槛与豁免规则

## 门槛

| 模块 | 行覆盖率门槛 | 说明 |
|---|---|---|
| `core/services/capabilities/*` | ≥ 85% | 单算法能力，逻辑重，必须严测 |
| `core/services/orchestrators/*` | ≥ 80% | 状态机/编排，必须覆盖各状态分支 |
| `core/views/*` | ≥ 75% | 参数校验 + 权限分支为主 |
| `core/models.py` | ≥ 90% | 字段约束、`save()` / `clean()` |
| `core/` 整体 | ≥ 70% | 不允许下降 |
| `ai-service` 整体 | ≥ 60% | 真模型路径走 `@pytest.mark.gpu`，豁免 |
| 前端 `stores/` + `api/` | ≥ 80% | 状态管理与接口适配层 |
| 前端整体 | ≥ 65% | 行覆盖 |

## 豁免

以下路径**可以**不计入覆盖率统计或不参与门槛：
- `*/migrations/*`
- `*/management/commands/*`（运维脚本）
- `core/util.py` 中纯调试/打印工具函数（如有）
- `ai-service/method/urn/` 中的模型权重加载与 CUDA 路径
- 任何 `if __name__ == "__main__":` 入口块
- 前端 `*.d.ts` 与生成文件（`auto-imports.d.ts` / `typed-router.d.ts` / `components.d.ts`）

## 基线建立流程

1. 完成第 7 节步骤 2（迁移已有测试）后跑一次：
   ```
   pytest --cov=core --cov-report=term-missing --cov-report=xml
   ```
2. 把当前覆盖率数字记在本文件下方，作为后续 PR 的最低线。
3. 若某次 PR 真的需要降低覆盖率（例如删了一大块死代码），在 PR 描述里说明原因并更新基线。

## 当前基线（待第一次跑出）

```
core/             —— TBD
core/services/    —— TBD
core/views/       —— TBD
core/models.py    —— TBD
```
