# 前后端主导的三路检测重构计划

## Summary
- 重构范围锁定在 `AIDetector/code/backend/backend-code`、`AIDetector/code/frontend/frontend-user`、`AIDetector/code/frontend/frontend-admin`。`AIDetector/code/ai-training/**` 完全不动；`AIDetector/code/ai-service/ai-service-code/**` 默认只保留现有图像推理通路，只有在本地论文/评审推理不可避免时才新增单独适配入口，不改训练/算法主体。
- 执行开始先落盘三份跟踪文件：根目录 `plan.md` 覆写为本计划；`prd.json` 重置为按下列 slice 排列的任务清单，初始状态全部为 `pending`；`progress.md` 清空后只写入 `持续运行直到所有prd.json里的任务都已完成`。
- 对外 API 路由优先保持不变：继续保留 `/api/upload/`、`/api/detection/submit/`、`/api/resource-task/create/`、`/api/detection-task/<id>/status/`、`/api/paper-results/<id>/`，重构只把业务逻辑从 `views_*` 抽离到服务层；必要时只新增补充型读取接口，不重命名既有入口。
- `prd.json` 每个任务统一字段：`id`、`title`、`status`、`slice`、`verification`、`attempts`、`fallback`。允许状态只有 `pending`、`in_progress`、`done`、`failed`；同一子任务累计尝试 10 次仍无法稳定通过验证时，必须标记 `failed`，写明 `fallback`，并切换到更简单实现继续推进。

## Slice Plan
1. `slice-00-tracking-bootstrap`：先整理跟踪机制，不改业务。文件只动根目录 `plan.md`、`prd.json`、`progress.md`。验证：`Get-Content plan.md`、`Get-Content progress.md`、`Get-Content prd.json | ConvertFrom-Json` 成功。
2. `slice-01-regression-baseline`：先补回归保护，锁住现有图像链路和当前论文/评审占位行为。新增 `core/tests/test_image_upload_flow.py`、`core/tests/test_image_detection_flow.py`、`core/tests/test_resource_task_flow.py`；必要时拆分现有 `core/tests.py` 到 `core/tests/`。验证：`conda run -n detect python manage.py test core.tests`。
3. `slice-02-backend-skeleton`：在 `core` 内建立五层落点，但不拆 app。新增 `core/services/resources/`、`core/services/orchestrators/`、`core/services/capabilities/`、`core/services/integrations/`、`core/services/event_logger.py` 及各自 `__init__.py`。把 `views_dectection.py`、`views_imageupload.py`、`views_review.py` 变成薄适配层。验证：`conda run -n detect python manage.py check`。
4. `slice-03-resource-layer`：抽离上传与预处理。新增 `core/services/resources/file_ingestion_service.py`、`core/services/resources/image_extraction_service.py`、`core/services/resources/document_preprocessor.py`；保留 `views_imageupload.py` 作为接口入口。图像任务继续抽图；论文/评审任务统一提取正文、段落、引用、图像索引。验证：图片、论文、评审三类上传 API 单测通过。
5. `slice-04-image-detection-adapter`：把现有图像能力封装成可复用能力层，不重写算法链。新增 `core/services/capabilities/image_detection_service.py`、`core/services/orchestrators/image_task_orchestrator.py`；复用 `local_detection.py`、`call_figure_detection.py`。验证：既有图像上传→提交→状态→结果→报告链路回归通过。
6. `slice-05-paper-closed-loop`：替换 `tasks.py` 里的 `run_paper_detection` 占位实现。新增 `core/services/orchestrators/paper_task_orchestrator.py`、`core/services/capabilities/text_detection_service.py`、`core/services/capabilities/reference_check_service.py`、`core/services/capabilities/llm_analysis_service.py`、`core/services/integrations/fastdetect_client.py`、`core/services/integrations/openai_client.py`。论文图像分析直接调用 `image_detection_service`；不在业务层直接写 `requests.post`。验证：`/api/resource-task/create/` 的 `paper` 任务能生成段落检测、可疑解释、参考文献结果。
7. `slice-06-review-closed-loop`：打通同行评审任务。新增 `core/services/orchestrators/review_task_orchestrator.py`、`core/services/capabilities/review_relevance_service.py`；收敛 `views_review.py` 里与资源型任务混杂的逻辑。评审检测只复用文本检测、预处理、LLM 相关性分析，不引入新的 AI 训练/推理目录。验证：原论文+评审文件上传、任务创建、状态轮询、逐段相关性结果查询通过。
8. `slice-07-persistence-split`：把文本结果从 `DetectionTask.text_detection_results` 中拆出来，但兼容一段时间。修改 `models.py`，新增 `PaperDetectionResult`、`PaperParagraphResult`、`PaperReferenceResult`、`ReviewDetectionResult`、`ReviewParagraphResult`；沿用 `ImageUpload`/`DetectionResult` 承载论文内抽出的图像检测结果。新增迁移 `core/migrations/0006_task_result_split.py`、`0007_review_result_split.py`。验证：`conda run -n detect python manage.py migrate` 与回归测试通过。
9. `slice-08-report-and-status-contract`：统一任务详情、结果聚合和报告生成。修改 `utils/report_generator.py`、`views_dectection.py`、必要时新增 `core/utils/task_result_serializer.py`。`/api/detection-task/<id>/status/` 输出按 `task_type` 规范化；`/api/paper-results/<id>/` 不再直接读 JSON 字段。验证：三类任务状态接口和报告下载接口均可用。
10. `slice-09-user-frontend-structure`：重构用户端页面组织，不改路由外观。保留 `pages/upload.vue`、`pages/history.vue`、`pages/step/[id].vue` 作为装配页；新增 `src/features/detection/components/DetectionTypeSwitcher.vue`、`ImageTaskForm.vue`、`PaperTaskForm.vue`、`ReviewTaskForm.vue`、`TaskProgressPanel.vue`、`src/features/results/PaperResultView.vue`、`ReviewResultView.vue`；拆分 `api/publisher.ts` 为 `api/detection.ts`、`api/resourceTasks.ts`、`api/reviewTasks.ts`。验证：`npm run type-check`、`npm run build-only`，并做上传页三种任务手工冒烟。
11. `slice-10-admin-frontend-structure`：管理端不做大改版，只把图像中心页面调整为任务类型感知。保留 `pages/files.vue`、`pages/reviews.vue`、`pages/logs.vue`、`pages/analytics.vue` 路由不变；新增 `src/features/tasks/TaskTypeFilter.vue`、`TaskSummaryTable.vue`、`src/features/logs/EventLogTable.vue`、`src/features/analytics/TaskTypeCharts.vue`；拆分 `src/api/file.ts`、`log.ts`、`review.ts`、`analytics.ts` 的混杂请求。验证：`npm run type-check`、`npm run build-only`，并检查管理端任务、日志、统计页能显示 `image/paper/review`。
12. `slice-11-ai-service-minimal-guardrail`：AI 服务默认不改；只有当必须补本地论文/评审入口时，才新增单一文件 `AIDetector/code/ai-service/ai-service-code/paper_review_entry.py` 或同等薄适配层，并禁止修改 `method/urn/**`、`method/llm/**`、`pipeline/**` 主体实现。验证：仅在该 slice 触发时执行本地调用冒烟；否则在 `prd.json` 标记 `done` 且备注 `no_change_needed`。
13. `slice-12-final-cleanup`：移除已弃用直连逻辑，保留兼容适配器。删除 `tasks.py` 中旧的 FastDetectGPT 直写流程、压缩 `views_*` 中遗留业务分支、把 `DetectionTask.text_detection_results` 改为兼容只读或迁移后删除。验证：全量测试、前后端构建、三类任务端到端冒烟全部通过后才允许收尾。

## Verification
- 每个 slice 完成后立即更新 `prd.json` 单项状态和 `progress.md`，不得跨 slice 累积未验证改动。
- 后端每步最少执行：`conda run -n detect python manage.py check`；涉及模型/迁移时再执行 `conda run -n detect python manage.py migrate` 与 `conda run -n detect python manage.py test core.tests`。
- 用户端每步执行 `npm run type-check`、`npm run build-only`；管理端同样执行 `npm run type-check`、`npm run build-only`。
- 关键冒烟顺序固定为：图像任务上传与检测、论文任务上传与结果查询、评审任务上传与结果查询、管理端任务列表、管理端日志/统计。
- 若某步验证失败，先在当前 slice 内修复；同一子任务累计 10 次仍失败，则 `prd.json` 标记 `failed`，记录失败原因与 fallback，例如“保留旧接口 + 新增只读结果聚合层”，然后进入下一个可推进 slice。
- 每次任一 slice 验证成功后，必须立刻执行一次 git 管理闭环：提交当前变更并尝试 `git push`；若因网络或远端原因 push 失败，只记录失败信息，不阻塞后续 slice 推进。

## Assumptions
- 默认策略是“接口稳定、内部重构”：不引入新 Django app，不改现有前后端路由路径，不碰 `ai-training`。
- 论文和评审的文本检测首期只支持 API 模式；本地模式只保留能力层接口，不在本轮交付。
- 事件日志本轮只统一写入入口，不做完整模型中心和完整日志中心 UI；管理端仅扩展到能看见三类任务，不做最终信息架构大改。
