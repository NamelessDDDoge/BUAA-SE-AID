# 设计文档 ↔ 测试文件 双向映射表

来源：`AIDetector/概要设计.pdf` V3.0。每新增一个功能或接口，**必须**同步更新本表。
"占位" 标记表示骨架已建但内容是 `pytest.skip("TODO")`，等后续 PR 填实。

## 用户端功能（DTC-USER-x）

| 功能编号 | 设计单元 | 主测试文件 | 状态 |
|---|---|---|---|
| DTC-USER-1 | 注册组织 | `core/tests/integration/api/organization/test_organization_application_flow.py`；`tests/e2e/organization_lifecycle/` | 占位 |
| DTC-USER-2 | 注册登录 | `core/tests/integration/api/auth/test_auth_flow.py` | 占位 |
| DTC-USER-3 | AI 检测（图像） | `core/tests/integration/api/detection/test_image_detection_flow.py` | **已存在**（待迁入） |
| DTC-USER-3 | AI 检测（论文） | `core/tests/integration/api/detection/test_paper_detection_flow.py` | 占位 |
| DTC-USER-3 | AI 检测（同行评审） | `core/tests/integration/api/detection/test_review_detection_flow.py` | 占位 |
| DTC-USER-3 | 端到端 | `tests/e2e/{image,paper,peer_review}_detection/` | 占位 |
| DTC-USER-4 | 人工审核（发起） | `core/tests/integration/api/review/test_manual_review_request_flow.py`；`tests/e2e/manual_review_flow/` | 占位 |
| DTC-USER-5 | 个人主页 | `core/tests/integration/api/auth/test_profile.py` | 占位 |

## 管理端功能（DTC-ADMIN-x）

| 功能编号 | 设计单元 | 主测试文件 | 状态 |
|---|---|---|---|
| DTC-ADMIN-1 | 管理员登录 | `core/tests/integration/api/admin/test_admin_login.py` | 占位 |
| DTC-ADMIN-2 | 统计分析 | `core/tests/integration/api/admin/test_statistics.py` | 占位 |
| DTC-ADMIN-3 | 组织管理 | `core/tests/integration/api/admin/test_organization_management.py` | 占位 |
| DTC-ADMIN-4 | 用户管理 | `core/tests/integration/api/admin/test_user_management.py` | 占位 |
| DTC-ADMIN-5 | 任务管理 | `core/tests/integration/api/admin/test_task_management.py` | 占位 |
| DTC-ADMIN-6 | 人工审核审批 | `core/tests/integration/api/review/test_review_approval.py` | 占位 |
| DTC-ADMIN-7 | 日志记录 | `core/tests/integration/api/admin/test_logs.py` | 占位 |
| DTC-ADMIN-8 | 组织信息/配额 | `core/tests/integration/api/admin/test_org_quota.py` | 占位 |
| DTC-ADMIN-9 | 模型状态管理 | `core/tests/integration/api/llm/test_model_management.py` | 占位 |
| DTC-ADMIN-10 | 模型状态管理（接口层） | `core/tests/integration/api/llm/test_model_management.py` | 占位 |

## 数据表（18 张，来自《概要设计》第 5 节）

| 序号 | 表名 | 单测文件 | 状态 |
|---|---|---|---|
| 5.1 | OrganizationApplication | `core/tests/unit/models/test_organization_application.py` | 占位 |
| 5.2 | Organization | `core/tests/unit/models/test_organization.py` | 占位 |
| 5.3 | InvitationCode | `core/tests/unit/models/test_user_and_invitation.py` | 占位 |
| 5.4 | User | `core/tests/unit/models/test_user_and_invitation.py` | 占位 |
| 5.5 | PublisherReviewerRelationship | `core/tests/unit/models/test_publisher_reviewer_relationship.py` | 占位 |
| 5.6 | FileManagement | `core/tests/unit/models/test_file_management.py` | 占位 |
| 5.7 | DetectionTask | `core/tests/unit/models/test_detection_task.py` | 占位 |
| 5.8 | ImageUpload | `core/tests/unit/models/test_image_upload.py` | 占位 |
| 5.9 | PaperUpload | `core/tests/unit/models/test_paper_upload.py` | 占位 |
| 5.10 | ReviewUpload | `core/tests/unit/models/test_review_upload.py` | 占位 |
| 5.11 | DetectionResult | `core/tests/unit/models/test_detection_result.py` | 占位 |
| 5.12 | SubDetectionResult | `core/tests/unit/models/test_sub_detection_result.py` | 占位 |
| 5.13 | ReviewRequest | `core/tests/unit/models/test_review_request.py` | 占位 |
| 5.14 | ManualReview | `core/tests/unit/models/test_manual_review.py` | 占位 |
| 5.15 | ImageReview | `core/tests/unit/models/test_image_review.py` | 占位 |
| 5.16 | Feedback | `core/tests/unit/models/test_feedback.py` | 占位 |
| 5.17 | Log | `core/tests/unit/models/test_log.py` | 占位 |
| 5.18 | Notification | `core/tests/unit/models/test_notification.py` | 占位 |

## 四大技术难点

| 难点 | 测试承载 |
|---|---|
| 2.2.1 多方法图像检测算法 | `ai-service/tests/integration/test_method_combinations.py`；`core/tests/unit/services/capabilities/image/` |
| 2.2.2 同步桥接执行 / 首次模型加载耗时 | `core/tests/integration/api/detection/test_local_infer_subprocess.py` |
| 2.2.3 权限 / 组织 / 复核状态流转 | `core/tests/integration/permissions/`；`tests/e2e/manual_review_flow/` |
| 2.2.4 检测结果结构化与报告生成 | `core/tests/integration/report_generation/` |

## 接口（39 个，《概要设计》第 4 节）

骨架先按接口分组到 `core/tests/integration/api/{auth,organization,detection,review,admin,llm,notify}/`，每组下面至少一个 `test_*.py` 占位文件。具体每个接口对应的用例编号在文件内 docstring 里维护，避免本表过长。
