# BUAA-SE-AID

面向学术场景的 AI 鉴伪与人工复核协同系统。

当前仓库包含：

- 用户前端：`AIDetector/code/frontend/frontend-user`
- 管理前端：`AIDetector/code/frontend/frontend-admin`
- Django 后端：`AIDetector/code/backend/backend-code`
- 本地 AI 推理脚本：`AIDetector/code/ai-service/ai-service-code`
- 训练代码：`AIDetector/code/ai-training/ai-training-code`

这份 README 以当前仓库里真实生效的实现为准，不以历史方案、旧接口文档或理想目标图为准。

## 1. 当前交付范围

系统当前围绕三类任务展开：

1. 图像检测：对学术图像做拼接、模糊、对比度异常、修补等伪造检测。
2. 论文检测：对整篇论文做文本 AIGC 检测、可疑段落解释、参考文献检查，并复用图像检测能力分析论文中的图片。
3. 同行评审检测：对 Review 文本做 AIGC 检测，并和原论文做段落相关性分析。

同时保留人工复核、组织管理、通知、统计和报告下载等业务闭环。

## 2. 仓库结构

```text
.
├── README.md
├── AGENTS.md
├── plan.md
├── prd.json
├── progress.md
├── 需求文档4.21.md
└── AIDetector
    └── code
        ├── backend
        │   └── backend-code
        ├── frontend
        │   ├── frontend-user
        │   └── frontend-admin
        ├── ai-service
        │   └── ai-service-code
        └── ai-training
            └── ai-training-code
```

## 3. 技术栈

### 3.1 用户前端

- 目录：`AIDetector/code/frontend/frontend-user`
- 技术：Vue 3、Vite、Vuetify、Pinia、Vue Router、Axios

### 3.2 管理前端

- 目录：`AIDetector/code/frontend/frontend-admin`
- 技术：Vue 3、Vite、Vuetify、Pinia、Vue Router、Axios、ECharts

### 3.3 后端

- 目录：`AIDetector/code/backend/backend-code`
- 技术：Django 5、Django REST Framework、JWT、ReportLab、PyMuPDF
- 默认数据库：SQLite
- 可选数据库：阿里云 PostgreSQL（可选 SSH 隧道）

### 3.4 本地 AI 推理

- 目录：`AIDetector/code/ai-service/ai-service-code`
- 形式：不是常驻 HTTP 服务，而是由后端按需拉起的本地 Python 子进程
- 当前默认启用的图像方法：`urn_coarse_v2`

### 3.5 训练代码

- 目录：`AIDetector/code/ai-training/ai-training-code`
- 作用：训练、实验、算法复现，不属于当前线上主链路

## 4. 后端五层架构

当前后端按下面五层组织，`integrations` / `llm client` 视为能力层内部的外部适配目录，而不是第六层。

| 层 | 当前目录 / 文件 | 作用 |
| --- | --- | --- |
| 接口层 | `core/views/`、`core/urls.py` | 接收请求、校验参数、调用 service/orchestrator、返回接口结果 |
| 资源层 | `core/services/resources/` | 上传落盘、图片抽取、文档预处理、文本清洗、文件关联 |
| 编排层 | `core/services/orchestrators/` | 负责任务创建、异步启动、状态推进、异常收敛、结果入库时序 |
| 能力层 | `core/services/capabilities/` | 图像检测、文本检测、可疑段落解释、参考文献检查、Review 相关性分析 |
| 存储层 | `core/models.py`、`core/utils/task_result_store.py`、`core/utils/task_result_serializer.py`、`core/utils/report_generator.py` | 持久化任务、资源、结果、报告和结果序列化 |

### 4.1 接口层

主要入口：

- `core/views/views_imageupload.py`
- `core/views/views_dectection.py`
- `core/views/views_review.py`
- `core/views/views_user.py`
- `core/views/views_admin.py`

当前接口层目标是“薄适配层”，不再直接承载上传、抽图、编排和外部调用细节。

### 4.2 资源层

主要文件：

- `core/services/resources/upload_service.py`
- `core/services/resources/image_extraction_service.py`
- `core/services/resources/document_preprocessor.py`
- `core/services/resources/text_sanitizer.py`

资源层负责：

- 上传文件校验与落盘
- `image / paper / review_paper / review_file` 资源类型归一化
- PDF / ZIP 抽图
- 论文与 Review 文档文本提取、段落切分、引用粗提取

### 4.3 编排层

主要文件：

- `core/services/orchestrators/image_task_orchestrator.py`
- `core/services/orchestrators/resource_task_orchestrator.py`
- `core/services/orchestrators/paper_task_orchestrator.py`
- `core/services/orchestrators/review_task_orchestrator.py`

编排层负责：

- 创建 `DetectionTask`
- 绑定资源文件
- 决定本地异步执行方式
- 更新 `pending / in_progress / completed / failed`
- 调用结果持久化与报告生成

### 4.4 能力层

主要文件：

- `core/services/capabilities/image_detection_service.py`
- `core/services/capabilities/image/local_detection.py`
- `core/services/capabilities/image/local_inference_client.py`
- `core/services/capabilities/text_detection_service.py`
- `core/services/capabilities/llm_analysis_service.py`
- `core/services/capabilities/reference_check_service.py`
- `core/services/capabilities/review_relevance_service.py`
- `core/services/capabilities/llm/fastdetect_client.py`
- `core/services/capabilities/llm/openai_client.py`

能力层负责：

- 图像鉴伪主能力
- 论文 / Review 的文本 AIGC 检测
- 可疑段落解释
- 参考文献存在性 / 相关性判断
- Review 与论文段落相关性分析

其中图像检测虽然已经被包进 `core/services/capabilities/image/`，但真实核心仍然是：

- `core/services/capabilities/image/local_detection.py`
- `core/services/capabilities/image/local_inference_client.py`
- `AIDetector/code/ai-service/ai-service-code/local_infer.py`

### 4.5 存储层

主要文件：

- `core/models.py`
- `core/utils/task_result_store.py`
- `core/utils/task_result_serializer.py`
- `core/utils/report_generator.py`

当前结果模型分层如下：

- 图像任务：`ImageUpload`、`DetectionResult`、`SubDetectionResult`
- 论文任务：`PaperDetectionResult`、`PaperParagraphResult`、`PaperReferenceResult`
- Review 任务：`ReviewDetectionResult`、`ReviewParagraphResult`

## 5. 当前真实执行链路

### 5.1 图像检测

主链路：

1. 前端调用 `/api/detection/submit/`
2. `views_dectection.py` 收请求
3. `image_task_orchestrator.py` 创建图像任务
4. 后端本地线程启动异步执行
5. `image_detection_service.py` 调 `image/local_detection.py`
6. `local_detection.py` 打包 `img.zip + data.json`
7. `local_inference_client.py` 拉起 `ai-service-code/local_infer.py`
8. `local_infer.py -> pipeline_single_image.py -> SingleImageMethod.py -> method/urn/infer.py`
9. 后端解析 stdout 结果并写入 `DetectionResult / SubDetectionResult`
10. `report_generator.py` 生成图像任务 PDF 报告

### 5.2 论文检测

主链路：

1. 前端上传 `paper`
2. `upload_service.py` 创建 `FileManagement(resource_type='paper')`
3. 前端调用 `/api/resource-task/create/`，`task_type='paper'`
4. `resource_task_orchestrator.py` 创建 `DetectionTask(task_type='paper')`
5. 本地线程启动 `paper_task_orchestrator.py`
6. `document_preprocessor.py` 提取正文、段落、分段、参考文献
7. `text_detection_service.py` 逐段调用 `fastdetect_client.py`
8. `llm_analysis_service.py` 为可疑段落生成说明
9. `reference_check_service.py` 做引用存在性 / 相关性检查
10. 如启用抽图，`image_extraction_service.py` 抽图并复用图像检测能力
11. `task_result_store.py` 持久化到论文结果表
12. `report_generator.py` 生成论文任务 PDF 报告

### 5.3 同行评审检测

主链路：

1. 上传 `review_paper` 与 `review_file`
2. `review_file.linked_file` 关联原论文
3. 前端调用 `/api/resource-task/create/`，`task_type='review'`
4. `resource_task_orchestrator.py` 创建 Review 任务
5. 本地线程启动 `review_task_orchestrator.py`
6. `document_preprocessor.py` 分别处理原论文与 Review 文本
7. `text_detection_service.py` 对 Review 分段做文本检测
8. `llm_analysis_service.py` 生成可疑 Review 段落解释
9. `review_relevance_service.py` 做 Review / 原文相关性分析
10. `task_result_store.py` 持久化到 Review 结果表
11. `report_generator.py` 生成 Review 任务 PDF 报告

## 6. 当前“纯本地化”边界

### 6.1 已经本地化的部分

当前代码已经去掉了对云端任务调度的硬依赖，真实执行方式是：

- 不依赖 Celery broker / Redis worker
- 资源任务通过 `transaction.on_commit(...) + 本地线程` 启动
- 图像检测 AI service 不是云服务，而是本地 Python 子进程
- 默认数据库是本地 SQLite

也就是说，任务调度、任务编排、图像推理触发方式已经是“本地执行路径优先”。

### 6.2 仍然允许云端的部分

- 数据库可以切换到阿里云 PostgreSQL
- 可选通过 SSH 隧道接入云端数据库

### 6.3 仍然不是完全离线的部分

按当前代码现实，论文 / Review 的文本检测默认仍会访问外部 HTTP 接口：

- `core/services/capabilities/llm/fastdetect_client.py`

因此：

- 图像检测链路可以做到纯本地推理
- 论文 / Review 任务的“任务启动与编排”是本地的
- 但文本段落检测目前默认不是完全离线实现

README 这里故意按代码现实描述，不把它写成“全链路完全离线”。

### 6.4 DOCX 支持的现实状态

代码中保留了 `document_preprocessor.py` 的 `.docx` 分支，也允许上传 `.docx`：

- `upload_service.py`
- `document_preprocessor.py`

但当前 `detect` 环境快照里没有安装 `python-docx`。因此本 README 锁定的安装方案保证的是：

- PDF
- TXT
- ZIP
- 图像任务本地推理链

如果你要启用 `.docx` 解析，需要先为团队环境补充并锁定 `python-docx`，再更新 `requirements.txt`。

## 7. 依赖与安装

### 7.1 当前锁定环境

本仓库当前以 `detect` conda 环境为标准环境。

- Python：`3.10.20`
- 推荐平台：Windows + PowerShell
- 原因：当前报告生成代码直接依赖 Windows 字体路径 `C:/Windows/Fonts/simsun.ttc`

如果你换到 Linux / macOS，需要自行处理：

- 中文字体路径
- 可能的 CUDA / Torch 轮子差异

### 7.2 锁定 requirements 的位置

后端锁定依赖文件：

- `AIDetector/code/backend/backend-code/requirements.txt`

这份文件是按当前 `detect` 环境版本手动收敛后的可运行集，不是原样整份 `pip freeze`。

排序原则：

1. 先装基础数值栈
2. 再装图像 / PDF / CV 依赖
3. 再装 Torch 与本地图像推理栈
4. 再装 Django / API 层
5. 最后装可选云数据库驱动

这样做是为了尽量降低 Windows + CUDA 环境下的安装偏差。

### 7.3 创建 conda 环境

在仓库根目录执行：

```powershell
conda create -n detect python=3.10.20 -y
conda activate detect
python -m pip install --upgrade pip setuptools wheel
```

如果你的 conda 源没有 `3.10.20`，可以退一步使用：

```powershell
conda create -n detect python=3.10 -y
```

### 7.4 安装后端依赖

```powershell
Set-Location AIDetector\code\backend\backend-code
pip install -r requirements.txt
```

说明：

- `requirements.txt` 顶部已经包含 PyTorch CUDA 12.1 的额外索引。
- 当前锁定环境对应的是 `torch==2.5.1+cu121` 与 `torchvision==0.20.1+cu121`。
- 如果你的机器没有对应 CUDA 环境，这份 requirements 不能保证本地图像推理链可直接运行。

### 7.5 初始化后端环境

```powershell
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

## 8. `.env` 配置

后端环境变量样例文件：

- `AIDetector/code/backend/backend-code/.env.example`

最重要的配置项如下：

| 变量 | 作用 | 默认建议 |
| --- | --- | --- |
| `DATABASE_MODE` | 数据库模式 | `local` |
| `LOCAL_DB_NAME` | 本地 SQLite 文件名 | `db.sqlite3` |
| `ALIYUN_DB_*` | 阿里云 PostgreSQL 配置 | 按需填写 |
| `ALIYUN_DB_USE_SSH_TUNNEL` | 是否启用 SSH 隧道 | `False` |
| `AI_SERVICE_DIR` | 本地 AI service 根目录 | 指向 `AIDetector/code/ai-service/ai-service-code` |
| `AI_TEST_DIR` | 本地 AI service 输入输出目录 | 默认即可 |
| `DJANGO_ALLOWED_HOSTS` | Django host 白名单 | `127.0.0.1,localhost` |

补充说明：

- `AI_SERVICE_DIR` 留空时，后端会尝试自动发现仓库内的 `ai-service-code`
- 图像任务本地推理默认直接使用当前 Python 解释器
- 如需强制指定解释器，可设置 `AI_SERVICE_PYTHON`

## 9. 前端安装与启动

### 9.1 用户前端

```powershell
Set-Location AIDetector\code\frontend\frontend-user
npm install
npm run dev
```

### 9.2 管理前端

```powershell
Set-Location AIDetector\code\frontend\frontend-admin
npm install
npm run dev
```

## 10. 推荐阅读顺序

如果你要继续开发这个项目，建议按下面顺序读代码：

### 10.1 总体先读

1. `README.md`
2. `plan.md`
3. `需求文档4.21.md`

### 10.2 后端主线

1. `core/models.py`
2. `core/views/views_imageupload.py`
3. `core/views/views_dectection.py`
4. `core/services/resources/upload_service.py`
5. `core/services/orchestrators/resource_task_orchestrator.py`
6. `core/services/orchestrators/paper_task_orchestrator.py`
7. `core/services/orchestrators/review_task_orchestrator.py`
8. `core/services/capabilities/image/local_detection.py`
9. `core/services/capabilities/image/local_inference_client.py`
10. `core/utils/task_result_store.py`
11. `core/utils/report_generator.py`

### 10.3 本地 AI 推理主线

1. `ai-service-code/local_infer.py`
2. `ai-service-code/pipeline/pipeline_single_image.py`
3. `ai-service-code/method/SingleImageMethod.py`
4. `ai-service-code/method/urn/infer.py`
5. `ai-service-code/Config.py`

## 11. 当前结论

这个项目当前最准确的描述不是“所有能力都已经完全统一收敛”，而是：

- 后端主结构已经按五层落地
- 图像、论文、Review 三类任务已经在同一任务模型下运行
- 资源任务启动链路已经是本地线程 / 本地子进程优先
- 图像推理链路是本地执行
- 数据库仍可切换到云端 PostgreSQL
- 论文 / Review 的文本检测目前默认仍依赖外部 FastDetect HTTP 接口
- DOCX 代码路径存在，但当前锁定环境尚未把 `python-docx` 纳入依赖快照

如果后续继续收敛，优先建议：

1. 把文本检测能力替换成真正本地实现，或至少把外部接口依赖明确配置化。
2. 为 `.docx` 处理补齐 `python-docx` 并完成版本锁定。
3. 继续清理历史兼容壳，让图像能力入口和命名更统一。
