持续运行直到所有prd.json里的任务都已完成

- 2026-04-21 14:39 +08:00 `slice-00-tracking-bootstrap` 已完成：根目录 `plan.md`、`prd.json`、`progress.md` 已按三路检测重构计划重置，并补充“每次验证成功后自动 commit 并尝试 push”的执行约束；验证通过 `Get-Content plan.md`、`Get-Content progress.md`、`Get-Content prd.json | ConvertFrom-Json`。
