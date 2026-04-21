### **2025-04-29 更新说明**
1. **User**  
   * 新增 `permission`、`reset_code`、`reset_code_expiry` 字段  
   * 增加 `related_reviewers` 多对多与 **PublisherReviewerRelationship** 中间表  
2. **FileManagement**  
   * 新增 `tag` 字段（五类）  
3. **DetectionTask**  
   * 新增 `report_file` 字段（生成的 PDF）  
4. **ImageUpload**  
   * 新增与任务的外键 `detection_task_id`  
   * 新增检测/审核状态字段 `isDetect` `isReview` `isFake`  
5. **DetectionResult**  
   * 新增补充信息字段：`llm_judgment` `ela_image` `exif_photoshop` `exif_time_modified`  
6. **SubDetectionResult** — 子检测方法结果表（1 图 × N 方法）  
7. **ReviewRequest / ManualReview / ImageReview**  
   * 完整支持多人图片级人工审核  
8. **Log**  
   * 记录四种操作类型  
9. 所有 DateTime 关键列已加索引（见表格）  

---

# 数据库表结构

| # | 表 | 说明 |
|---|----|------|
| 1 | **User** | 用户 & 角色（发布者 / 审核员） |
| 2 | **PublisherReviewerRelationship** | 发布者-审核员指派关系（多对多中间表） |
| 3 | **FileManagement** | 源文件（png / jpg / zip / pdf…） |
| 4 | **DetectionTask** | 一次送检的打包任务 |
| 5 | **ImageUpload** | 由 FileManagement 提取的单张图片 |
| 6 | **DetectionResult** | AI 对单图的总检测结果 |
| 7 | **SubDetectionResult** | 7 + n 种子方法概率 & mask |
| 8 | **ReviewRequest** | 发布者发起的人工审核申请 |
| 9 | **ManualReview** | 审核员对申请的整体审核 |
|10 | **ImageReview** | 审核员对单图的逐项评分 |
|11 | **Feedback** | 发布者/其他人对审核的点赞 & 评论 |
|12 | **Log** | 全局操作日志 |

---

## 1. User

| Column | Type | Constraints / 默认 |
|--------|------|--------------------|
| id | INT PK | |
| username | VARCHAR | **Unique** |
| email | EMAIL | **Unique** |
| password | VARCHAR | |
| role | ENUM(publisher, reviewer) | 默认 `publisher` |
| permission | INT | 自动随 role 设置（1110/1） |
| profile | TEXT | Nullable |
| avatar | IMAGE | Nullable；默认 `avatars/default_avatar.png` |
| reset_code | CHAR(6) | Nullable |
| reset_code_expiry | DATETIME | Nullable |
| date_joined | DATETIME | INDEX |
| last_login | DATETIME | |
| …Django 其他字段… |

`related_reviewers (M2M)` → **PublisherReviewerRelationship**

---

## 2. PublisherReviewerRelationship (中间表)

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| publisher_id | FK → User(id) | 限 `role='publisher'` |
| reviewer_id | FK → User(id) | 限 `role='reviewer'` |
| created_at | DATETIME | auto |
| is_active | BOOLEAN | 默认 True |

`unique_together(publisher_id, reviewer_id)`

---

## 3. FileManagement

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| user_id | FK → User |
| file_name | VARCHAR |
| file_size | BIGINT |
| file_type | VARCHAR |
| tag | ENUM(Biology, Medicine, Chemistry, Graphics, Other) | 默认 `Other` |
| upload_time | DATETIME | INDEX |

---

## 4. DetectionTask

| Column | Type | Constraints / 默认 |
|--------|------|--------------------|
| id | INT PK |
| user_id | FK → User |
| task_name | VARCHAR |
| status | ENUM(pending, in_progress, completed) | 默认 `pending` |
| upload_time | DATETIME |
| completion_time | DATETIME | Nullable |
| report_file | FILE | Nullable (`reports/…`) |

---

## 5. ImageUpload

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| detection_task_id | FK → DetectionTask | Nullable |
| file_management_id | FK → FileManagement |
| image | IMAGE (`extracted_images/`) |
| extracted_from_pdf | BOOLEAN |
| page_number | INT | Nullable |
| upload_time | DATETIME |
| isDetect | BOOLEAN | 是否已送 AI |
| isReview | BOOLEAN | 是否已送人工 |
| isFake | BOOLEAN | AI 结果快速标记 |

---

## 6. DetectionResult

| Column | Type | Constraints / 说明 |
|--------|------|--------------------|
| id | INT PK |
| image_upload_id | FK → ImageUpload |
| detection_task_id | FK → DetectionTask | Nullable |
| is_fake | BOOLEAN | Nullable |
| confidence_score | FLOAT | Nullable |
| detection_time | DATETIME | INDEX |
| status | ENUM(in_progress, completed) | 默认 |
| is_under_review | BOOLEAN | |
| review_request_id | O2O FK → ReviewRequest | Nullable |
| llm_judgment | TEXT | Nullable |
| ela_image | IMAGE (`ela_results/`) | Nullable |
| exif_photoshop | BOOLEAN | Nullable |
| exif_time_modified | BOOLEAN | Nullable |

---

## 7. SubDetectionResult

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| detection_result_id | FK → DetectionResult |
| method | ENUM(method1 … method7, big_model_method …) |
| probability | FLOAT |
| mask_image | IMAGE (`masks/`) | Nullable |
| mask_matrix | JSON | 256 × 256 矩阵 |
| created_at | DATETIME |

`unique_together(detection_result_id, method)`

---

## 8. ReviewRequest   (发布者→审核员)

| Column | Type | Constraints / 默认 |
|--------|------|--------------------|
| id | INT PK |
| detection_result_id | FK → DetectionResult |
| user_id | FK → User | 申请人 |
| request_time | DATETIME | INDEX |
| status1 | ENUM(pending, in_progress, completed) | 发布者视角 |
| status2 | ENUM(pending, refused, accepted) | 管理员视角 |
| reason | TEXT |
| review_start_time | DATETIME | Nullable |
| review_end_time | DATETIME | Nullable |
| reviewers | M2M → User | 指定审核员 |
| check_status | ENUM(refused, accepted) | 管理员最终决定 |
| check_reason | TEXT |

`imgs (M2M) → ImageUpload`

---

## 9. ManualReview   (审核员对一次申请的整体意见)

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| review_request_id | FK → ReviewRequest |
| reviewer_id | FK → User |
| status | ENUM(undo, completed) | 默认 `undo` |
| review_time | DATETIME | INDEX |

`imgs (M2M) → ImageUpload`  
`img_reviews (M2M) → ImageReview`

---

## 10. ImageReview   (审核员对单张图的 7 项评分)

| Column | Type | 说明 |
|--------|------|------|
| id | INT PK |
| manual_review_id | FK → ManualReview |
| img_id | FK → ImageUpload |
| score1 … score7 | INT | Nullable |
| reason1 … reason7 | TEXT | Nullable |
| result | BOOLEAN | 最终真假 |
| review_time | DATETIME | INDEX |

---

## 11. Feedback

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| manual_review_id | FK → ManualReview |
| user_id | FK → User |
| is_like | BOOLEAN |
| comment | TEXT | Nullable |
| feedback_time | DATETIME |

---

## 12. Log

| Column | Type | Constraints |
|--------|------|-------------|
| id | INT PK |
| operation_time | DATETIME |
| user_id | FK → User |
| operation_type | ENUM(upload, detection, review_request, manual_review) |
| related_model | VARCHAR |
| related_id | INT |

---