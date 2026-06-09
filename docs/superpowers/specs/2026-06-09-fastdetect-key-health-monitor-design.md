# FastDetect Key 健康监控 — 设计文档

- 日期：2026-06-09
- 状态：待实现
- 分支：main-test-entry

## 背景

后端通过 FastDetect 服务做 AIGC 段落检测。已上传多把 API key 用于 fallback，每把 key
对应一行 `LLMModel`（`model_type='fastdetect'`）。当前 fallback 机制（`fastdetect_client.py`）
在某些 HTTP 状态下切换到下一把 key，但：

1. `runtime_config.get_fastdetect_keys` 把所有 active 行的 key **打平 + 去重**成一个扁平列表
   （`runtime_config.py:68`），丢失了 key 与 `LLMModel` 行的对应关系，无法把一次失败映射回某行。
2. fallback 不持久化任何状态，超级管理员无法看到哪把 key 可用。
3. "不可用"只能靠超时/异常猜，无明确判定。

需求：在超级管理员前端实时监控哪些 key 可用；访问发现额度耗尽时**明确**标记不可用（非靠超时）。

## 实测证据（detect 环境，真实打 `/api/detect`）

| 情况 | 返回 |
|---|---|
| 成功 | `HTTP 200` + `{"code":0,"data":{...,"prob":0.48},"msg":"Succeed"}` |
| 额度耗尽 | `HTTP 402` + `{"code":402,"msg":"Key credit exhausted (100.0000/100.0000)","data":null}` |
| 密钥无效 / 端点错 | `HTTP 401` + `{"error":{"type":"authentication_error",...}}` |

关键结论：

- **额度耗尽明确可判**：`HTTP 402` / body `code==402` / msg 含 `credit exhausted`。无需靠超时。
- 402 的 msg 暴露额度数字 `(已用/总额)`；但**仅耗尽时**显示，成功响应不含剩余额度。
  → 无法做"实时剩余额度数字"，只能做"可用/不可用"判定 + 把耗尽时的数字并入错误文本展示。
- FastDetect API **无**额度/余额查询接口（openapi.json 仅 `/`、`/health`、`/api/detect`、`/api/web-detect`）。
- 发现脏配置：`LLMModel` row 4/5 的 endpoint 被误填为 `https://api.deepseek.com/chat/completions`，
  应为 fastdetect 端点。

## 目标

- 超级管理员前端按 key 展示健康状态，可手动触发检测。
- 检测/访问遇到额度耗尽或密钥无效时，明确标记对应 key 不可用并持久化原因。
- 暂时性故障（限流/超时/5xx）不误判为"死"。

## 非目标

- 不做后台定时探测（用户选被动 + 手动）。
- 不存独立额度数字字段（数字并入 `last_error` 文本）。
- 不查 FastDetect 余额接口（不存在）。

## 数据模型

`LLMModel` 加字段（新 migration），语义上仅 `fastdetect` 行使用：

| 字段 | 类型 | 说明 |
|---|---|---|
| `health_status` | CharField(choices, default `unknown`) | `unknown` / `available` / `exhausted` / `invalid` / `error` |
| `last_checked_at` | DateTimeField(null) | 最近一次检测/访问时间 |
| `last_error` | TextField(null) | 最近失败 msg，如 `Key credit exhausted (100/100)` |

状态枚举含义：
- `available`：最近一次调用成功
- `exhausted`：额度耗尽（402）
- `invalid`：密钥无效 / 认证失败（401/403）
- `error`：暂时性故障（429/408/5xx/超时/连接错）
- `unknown`：从未检测过

## 判定逻辑（共享）

新建 `core/services/capabilities/llm/health.py`：

```python
def classify_fastdetect_response(status, body):
    """返回 (health_status, detail_msg)。body 为 dict 或 None。"""
```

规则（基于实测）：
1. `status == 200` 且 `body.get("code") == 0` → `("available", "")`
2. `status == 402` 或 `body.get("code") == 402` 或 msg 含 `credit exhausted`
   → `("exhausted", msg)`，msg 含额度数字
3. `status in (401, 403)` → `("invalid", msg)`
4. `status in (408, 429)` 或 `status >= 500` → `("error", msg)`
5. 其余 4xx → `("error", msg)`（保守，不算死）

网络异常（ConnectionError/Timeout）由调用方归类为 `("error", repr(exc))`。

额度数字解析：正则 `\(([\d.]+)\s*/\s*([\d.]+)\)` 从 msg 抠出，保留在文本里展示。

## 被动更新流程

重构 `fastdetect_client.detect_text_segment`，使其遍历**行**（保留 `LLMModel.id`）而非扁平 key：

- 新增 `runtime_config.get_fastdetect_candidates()` 返回 `[(model_id_or_None, endpoint, detector, key), ...]`，
  保留行身份；显式 arg / 环境变量来源的 key `model_id=None`（无行可更新）。
- 每把 key 调用后用 `classify_fastdetect_response` 归类：
  - `available` → 若有 model_id，更新行 `health_status='available'`、清 `last_error`、`last_checked_at=now`；返回结果
  - `exhausted` / `invalid` → 更新对应行状态 + `last_error`，继续下一把
  - `error` → 更新对应行 `health_status='error'` + `last_error`，继续下一把
- 修正当前"最后一把 key 不进入 fallback 判定"的问题：所有 key 一视同仁分类；全部失败后抛最后一个异常。
- health 写库失败不得影响检测主流程（try/except 包裹，记 warning）。

## 接口（`views_llm`）

`LLMModelViewSet` 加 action（权限 `IsSoftwareAdmin`）：

- `POST /admin/llms/{id}/probe/`：对该行打一次极小 detect（固定短文本），用共享判定更新该行 health，返回
  `{health_status, last_error, last_checked_at}`。
- `POST /admin/llms/probe_all/`：遍历所有 `fastdetect` 行各探测一次，返回汇总列表。

`LLMModelSerializer` 增加只读字段 `health_status`、`last_checked_at`、`last_error`。

## 前端 `frontend-admin/src/pages/llms.vue`

- `api/llm.ts`：`LLMModel` 接口加只读 `health_status`/`last_checked_at`/`last_error`；新增
  `probeLLMModel(id)`、`probeAllLLMModels()`。
- 表格新增「健康状态」列：chip 显示
  - 可用（绿 success）/ 额度耗尽（红 error）/ 密钥无效（灰）/ 异常（橙 warning）/ 未知（默认）
  - 副文本：`last_checked_at` 相对时间；hover tooltip 显示 `last_error`
- 每行加「测试」按钮 → `probeLLMModel` → 刷新该行。
- 顶部加「全部测试」按钮 → `probeAllLLMModels` → 刷新列表。
- 仅 `fastdetect` 行展示健康列内容；`chat` 行留空或 `—`。

## 脏配置修正

实现阶段顺手修正 row 4/5 的 endpoint（误填 deepseek → fastdetect 默认端点）。
属生产数据变更，已获授权。改后用 probe 验证这两把 key 的真实状态（可能 available / exhausted / invalid）。

## 测试（detect 环境）

- 单元：`classify_fastdetect_response` 覆盖五类分支（200/402/401/429/超时归类）+ 额度数字解析。
- 单元：`get_fastdetect_candidates` 保留行身份、去重、来源优先级。
- 集成：`probe` / `probe_all` action 鉴权 + 状态写库（mock `requests.post`）。
- 集成：`detect_text_segment` 被动更新行状态（mock 各类响应）。

## 风险与权衡

- 被动更新写库引入额外 DB 写；用 try/except 隔离，不阻塞检测。
- `unknown` → 需手动或首次访问后才有状态；可接受（用户选被动 + 手动）。
- 多把 key 指向同一行（逗号分隔）场景不在本设计内 —— 已确认每 key 一行。
```
