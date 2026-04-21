持续运行直到 `prd.json` 里的任务全部完成。

- 2026-04-21 14:39 +08:00 `slice-00-tracking-bootstrap` 已完成：根目录 `plan.md`、`prd.json`、`progress.md` 已切换到三路检测重构跟踪，并写入“每次验证成功后自动 commit 并尝试 push”的执行约束；验证通过 `Get-Content plan.md`、`Get-Content progress.md`、`Get-Content prd.json | ConvertFrom-Json`。
- 2026-04-21 15:00 +08:00 计划文档已细化并显式吸收 `架构共识.md`：补充固定前提、模型调用入口长期约束、三类任务共享五层架构与统一事件日志等约束；验证通过 `rg` 命中检查与 `Get-Content plan.md`。
- 2026-04-21 15:24 +08:00 `slice-01-regression-baseline` 已完成：删除单体 `core/tests.py`，拆分为 `test_image_upload_flow.py`、`test_image_detection_flow.py`、`test_resource_task_flow.py` 三组回归测试，并修正本地 fake AI fixture 与当前解析器键名一致；验证通过 `DATABASE_MODE=local LOCAL_DB_NAME=db.sqlite3 conda run -n detect python manage.py test core.tests`。
