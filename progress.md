Keep running until every item in `prd.json` is completed.

- 2026-04-21 14:39 +08:00 `slice-00-tracking-bootstrap` completed: reset `plan.md`, `prd.json`, and `progress.md` for the three-lane detection refactor and recorded the verify-then-commit workflow.
- 2026-04-21 15:00 +08:00 planning notes absorbed `架构共识.md`: fixed local-first assumptions, shared five-layer backend structure, and unified event logging constraints.
- 2026-04-21 15:24 +08:00 `slice-01-regression-baseline` completed: split backend regression coverage into `test_image_upload_flow.py`, `test_image_detection_flow.py`, and `test_resource_task_flow.py`, and aligned the local fake-AI fixtures with the current parser contract.
- 2026-04-21 15:46 +08:00 `slice-02-backend-skeleton` completed: created the `core/services/` layer skeleton, added `event_logger.py`, and routed upload/resource-task entry points through services and orchestrators instead of growing `views_*`.
- 2026-04-21 16:28 +08:00 `slice-03-resource-layer` completed: added `core/services/resources/image_extraction_service.py` and `document_preprocessor.py`, routed upload extraction and paper text preprocessing through those services, slimmed `core/views/views_imageupload.py`, and added regression coverage for zip image uploads plus document segmentation fallback.

Verification:
- `DATABASE_MODE=local LOCAL_DB_NAME=db.sqlite3 conda run -n detect python manage.py check`
- `DATABASE_MODE=local LOCAL_DB_NAME=db.sqlite3 conda run -n detect python manage.py test core.tests.test_image_upload_flow core.tests.test_resource_task_flow core.tests.test_resource_preprocessing`
