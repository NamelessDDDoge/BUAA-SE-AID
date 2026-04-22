# Workspace Tracking

This file is a local scratchpad for the coding agent.

Purpose:
- record the active task focus for this workspace
- note important local assumptions that should not be committed
- point to `progress.md` for completed work
- point to `prd.json` for near-term task status

Current focus:
- analyze the `AI鉴伪` architecture
- simplify image detection to a pure local execution path
- refresh repository documentation

Local environment rule:
- always use the `detect` conda environment for commands run under `C:\Users\admin\Desktop\SE\BUAA-SE-AID`
- every code or migration change must be followed by a full runtime verification pass before claiming completion; at minimum run migrations plus the relevant end-to-end or full test command for the affected app/workspace
- after every successful verification step, automatically run git management end-to-end: create a commit and attempt a push immediately; if push fails because of network or remote issues, record it and continue

成功调试案例：
- 案例：
  - 图像上传请求在 `/api/upload/` 返回 `500`。
  - 文件已经成功进入 `uploads/`，但请求仍然失败，前端无法继续进入“提取图片”或“创建检测任务”阶段。
- 问题分类：
  - 这是一次由重构引入的后端持久化 bug。
  - 更具体地说，是生成的媒体文件路径超过了数据库字段长度限制。
- 上一次 AI 具体犯的错：
  - 先误判成了文件格式白名单问题，去改 PDF 支持；但真实故障对普通图片上传同样成立。
  - 没有先从真实服务端 traceback 开始排查，导致优化了错误分支。
  - 测试只覆盖了短文件名的 happy path，没有覆盖真实生产里的长文件名场景。
- 实际根因：
  - `core/services/resources/image_extraction_service.py` 在 `slice-03` 中改了单图上传的落盘命名方式。
  - 原先是基于上传文件名生成一次提取图路径；重构后变成基于“已经带 UUID 前缀的 stored upload path”再次拼接新文件名。
  - 这会把长文件名信息重复带入，导致 `ImageUpload.image` 的值超过模型字段上限。
  - 在 Postgres 中，这个字段实际受 `varchar(100)` 约束，因此触发：
    - `django.db.utils.DataError: value too long for type character varying(100)`
  - 在 SQLite 测试中，这类问题可能漏掉，因为 SQLite 不会像 Postgres 一样严格执行这个长度限制。
- 正确识别这个 bug 的证据：
  - 用户提供的 traceback 直接指向：
    - `create_image_uploads_for_resource`
    - `store_uploaded_image`
    - `ImageUpload.objects.create(...)`
  - SQL 异常不是权限问题、不是解析问题，而是明确的 `StringDataRightTruncation`。
  - 文件已经成功保存到磁盘，说明失败发生在“初始上传之后、ImageUpload 记录创建期间”。
- 正确的复现方式：
  - 不能只用短文件名复现。
  - 必须补一个回归测试：上传一个刻意很长的图片文件名，并断言生成的 `ImageUpload.image.name` 不超过：
    - `ImageUpload._meta.get_field("image").max_length`
  - 这个测试与数据库后端无关，即使在 SQLite 下也能提前抓住问题。
- 正确的修复方案：
  - 不修改当前 schema。
  - 直接收敛 `core/services/resources/image_extraction_service.py` 中生成提取图路径的命名策略。
  - 新路径只基于以下短信息构造：
    - `file_management.id`
    - 一个短的、清洗过的 hint
    - 一个 UUID
    - 后缀名
  - 最终必须显式保证生成出的相对路径长度不超过 `ImageUpload.image.max_length`。
- 本次成功修复涉及的文件：
  - `AIDetector/code/backend/backend-code/core/services/resources/image_extraction_service.py`
  - `AIDetector/code/backend/backend-code/core/tests/test_image_upload_flow.py`
- 这类 bug 必须具备的回归测试：
  - 长文件名图片上传后，API 仍然成功
  - `ImageUpload.image.name` 长度 `<=` 字段上限
  - 现有普通图片、ZIP 图片、review paper、review file 上传测试仍然通过
  - 修复后，完整的 upload -> extract -> detection API 链路仍然通过
- 由此沉淀出的调试规则：
  - 当请求“部分成功”时，例如文件已经落盘但接口返回 `500`，必须把它当成分阶段流水线故障处理，先确定准确的失败阶段边界，再改代码。
  - 如果是存储/路径类问题，优先检查模型字段长度限制和生成出来的文件名，不要先改业务流、权限或格式校验。
  - 如果生产环境使用 Postgres、测试环境使用 SQLite，必须用显式断言把真实约束编码进测试里，不能假设 SQLite 会替你发现这类问题。
Urgent paper report bug case:
- Symptom:
  - A completed `paper` task returned a damaged/wrong `task_<id>_report.pdf`.
  - Reproducing with `task_7_report.pdf` showed the downloaded PDF was structurally valid, but its extracted text was an image-task report with fields like `cmd_block_size`, `urn_k`, image fake probabilities, and per-image method outputs.
- Root cause:
  - `core/services/orchestrators/paper_task_orchestrator.py` correctly reused image detection for extracted paper images.
  - But `core/local_detection.py` finalized any task with finished image sub-results by calling `generate_detection_task_report(...)` and writing `DetectionTask.report_file`.
  - Because `paper` tasks share the same `DetectionTask` model, the image subflow overwrote the generic task report slot before any paper-specific report existed.
  - `core/views/views_dectection.py` then served that file directly from `/api/tasks/<id>/report/`, so the user downloaded the wrong report for the task type.
- Required reproduction rule:
  - Use the real `task_7_report.pdf` fixture in an end-to-end regression:
    - upload via `/api/upload/`
    - create a `paper` task via `/api/resource-task/create/`
    - execute the local paper pipeline
    - download `/api/tasks/<id>/report/`
    - assert the returned PDF identifies itself as a paper report rather than an image report
- Correct fix rule:
  - Do not let image sub-results finalize non-`image` parent tasks.
  - Generate reports by `task_type`, not by the presence of `DetectionResult` rows.
  - Make completed `paper`/`review` downloads regenerate their dedicated report so stale bad `report_file` values self-heal.
