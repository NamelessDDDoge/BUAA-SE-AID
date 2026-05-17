# BUAA-SE-AID

面向学术场景的 AI 鉴伪与人工复核协同系统。

当前仓库包含两个前端、一个 Django 后端，以及一个由后端直接拉起的图像 AI 推理链路。当前支持两种运行方式：

- 服务器本地直接拉起 `local_infer.py`
- 服务器业务 + 通过 HTTP 桥接到笔记本 GPU 推理

图像鉴伪主链路当前不依赖 Redis 或 Celery。

## 仓库结构

```text
.
├── README.md
├── 图像鉴伪模块说明.md
├── AIDetector
│   ├── 用户使用手册.docx
│   └── code
│       ├── frontend
│       │   ├── frontend-user
│       │   └── frontend-admin
│       ├── backend
│       │   └── backend-code
│       ├── ai-service
│       │   ├── README.md
│       │   ├── AI推理服务启动方式.md
│       │   └── ai-service-code
│       └── ai-training
│           └── ai-training-code
├── create_demo_users.py
├── plan.md
├── prd.json
└── progress.md
```

## 子系统概览

### 用户前端

- 目录：`AIDetector/code/frontend/frontend-user`
- 技术栈：Vue 3 + Vite + Vuetify
- 职责：上传资源、提交检测、查看结果、发起人工复核

### 管理前端

- 目录：`AIDetector/code/frontend/frontend-admin`
- 技术栈：Vue 3 + Vite + Vuetify
- 职责：组织、用户、审核与统计管理

### 后端

- 目录：`AIDetector/code/backend/backend-code`
- 技术栈：Django + Django REST Framework + JWT
- 职责：账户体系、资源管理、检测任务、检测结果、报告生成、人工复核

图像鉴伪当前关键文件：

- `AIDetector/code/backend/backend-code/core/views/views_dectection.py`
- `AIDetector/code/backend/backend-code/core/services/orchestrators/image_task_orchestrator.py`
- `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_detection.py`
- `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_inference_client.py`
- `AIDetector/code/backend/backend-code/core/models.py`

### AI Service

- 目录：`AIDetector/code/ai-service/ai-service-code`
- 后端实际调用入口：`AIDetector/code/ai-service/ai-service-code/local_infer.py`
- 可选远程服务入口：`AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`
- 职责：读取批量图片和参数，执行图像鉴伪 pipeline，并把序列化结果回传给后端

更详细说明见：

- [AI Service 介绍文档](./AIDetector/code/ai-service/README.md)
- [AI 推理服务启动方式](./AIDetector/code/ai-service/AI推理服务启动方式.md)
- [图像鉴伪模块说明](./图像鉴伪模块说明.md)
- [图像检测并发改造设计说明](./图像检测并发改造设计说明.md)
- [图像检测联调与上线检查清单](./图像检测联调与上线检查清单.md)

## 当前图像检测链路

当前图像检测为“异步提交 + 后台受控并发执行”，核心流程如下：

1. 前端调用 `/api/detection/submit/`。
2. 后端 `submit_detection2` 创建 `DetectionTask`，并校验组织配额、任务参数与图片列表。
3. 后端将任务提交到图像检测执行池；普通图像任务走可控并发池，含 LLM 的图像任务走独立串行池。
4. `core/services/capabilities/image/local_detection.py` 为每批图片生成 `img.zip` 与 `data.json`。
5. 后端桥接层为每次推理创建独立 request 目录。
6. 若未配置 `AI_REMOTE_INFER_URL`，后端用子进程启动 `local_infer.py`。
7. 若配置了 `AI_REMOTE_INFER_URL`，后端将 request 目录中的 `img.zip` 与 `data.json` POST 到远程 GPU 推理服务。
8. 本地与远程模式下，AI service 都会使用 request 级缓存目录，而不是共享全局 cache。
9. `local_infer.py` 解压图片、载入参数、执行 `PipelineSingleImage.run_multi_images(...)`。
10. `PipelineSingleImage` 调用 `SingleImageMethod` 中的各个方法，得到 LLM、ELA、EXIF、CMD 和多个 URN 子方法结果。
11. AI Service 将结果 `pickle + base64` 后返回给后端。
12. 后端解析返回值，落库到 `DetectionResult` 与 `SubDetectionResult`，同时生成掩码图、ELA 图和任务报告。
13. 任务状态更新为 `completed` 或 `failed`，前端再通过结果接口拉取详情。

## AI Service 当前实现

当前实际生效的是“后端桥接层 + 本地推理脚本”模式，也支持“后端桥接层 + 远程 GPU 推理服务”模式。

### 入口与桥接

- 后端桥接层位于 `core/services/capabilities/image/local_inference_client.py`。
- 它负责准备 `img.zip` / `data.json`，设置 request 级工作目录、临时目录和 `TORCH_HOME`。
- 本地模式下，它会直接启动 `local_infer.py`。
- 远程模式下，它会把输入 POST 给 `gpu_infer_service.py`。

### AI Service 内部结构

- `local_infer.py`：单次推理入口，负责读入 zip 包和参数文件。
- `pipeline/pipeline_single_image.py`：当前后端实际使用的 pipeline。
- `method/SingleImageMethod.py`：聚合所有单图方法，并在初始化阶段加载 URN 模型权重。

### 当前方法列表

`SingleImageMethod.get_methods()` 当前顺序为：

1. `llm`
2. `ela`
3. `exif`
4. `cmd`
5. `urn_coarse_v2`
6. `urn_blurring`
7. `urn_brute_force`
8. `urn_contrast`
9. `urn_inpainting`

后端目前真正持久化为 `SubDetectionResult` 的是 5 个结构化子方法：

- `splicing`
- `blurring`
- `bruteforce`
- `contrast`
- `inpainting`

其中：

- `LLM` 结果写入 `DetectionResult.llm_judgment` 与可选 `llm_image`
- `ELA` 结果写入 `DetectionResult.ela_image`
- `EXIF` 结果转成 `exif_photoshop` / `exif_time_modified`
- URN/CMD 类结果被解析为总体真假判断、置信度和子方法掩码

### 当前运行约束

- 必须在本地可用 Python 环境中运行。
- 当前联调和测试中，仓库实际可用的是 `se` conda 环境。
- AI Service 的真实入口是脚本，不需要单独常驻启动。
- `SingleImageMethod.py` 初始化时会直接加载多组 URN 权重，因此首次启动成本较高。
- LLM 路径依赖额外模型与环境；当前实现中它被单独串行调度，不与普通图像任务共享并发池。
- 现有自动化测试不依赖真实 GPU，因为推理过程被 mock 或替换为测试夹具。

### 当前真实生效的环境变量

桥接层实际读取的是这些变量：

- `AI_SERVICE_DIR`
- `AI_SERVICE_ENTRYPOINT`
- `AI_SERVICE_PYTHON`
- `AI_SERVICE_TEST_DIR`
- `AI_SERVICE_TMP_DIR`
- `AI_SERVICE_TORCH_HOME`
- `AI_REMOTE_INFER_URL`
- `AI_REMOTE_INFER_TIMEOUT`
- `AI_REMOTE_INFER_TOKEN`
- `IMAGE_TASK_MAX_WORKERS`
- `AI_REMOTE_INFER_MAX_CONCURRENCY`

其中最常用的是：

- `AI_SERVICE_DIR`：AI Service 代码目录
- `AI_SERVICE_PYTHON`：用于启动 `local_infer.py` 的 Python 解释器
- `AI_REMOTE_INFER_URL`：远程 GPU 推理服务地址；设置后优先走远程推理
- `IMAGE_TASK_MAX_WORKERS`：普通图像任务执行池大小
- `AI_REMOTE_INFER_MAX_CONCURRENCY`：远程 GPU 服务最大并发度，默认建议保持 `1`

## 本地运行

当前仓库联调与测试建议优先使用 `se` conda 环境。

### 后端

工作目录：

- `AIDetector/code/backend/backend-code`

最小命令：

```powershell
conda activate se
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

### 用户前端

工作目录：

- `AIDetector/code/frontend/frontend-user`

命令：

```powershell
npm install
npm run dev
```

### 管理前端

工作目录：

- `AIDetector/code/frontend/frontend-admin`

命令：

```powershell
npm install
npm run dev
```

### AI Service

本地模式下，AI Service 不需要单独启动常驻进程。只要后端环境可用，后端会在处理图像任务时直接启动：

- `AIDetector/code/ai-service/ai-service-code/local_infer.py`

远程 GPU 模式下，需要在笔记本额外启动：

- `AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`

建议至少确认：

- `AI_SERVICE_DIR` 指向 `AIDetector/code/ai-service/ai-service-code`
- `AI_SERVICE_PYTHON` 与当前可用环境一致
- 本地模型权重已经放在算法代码要求的位置
- 若使用笔记本 GPU，则已正确配置 `AI_REMOTE_INFER_URL`

## 当前已移除的旧链路

当前图像检测主链路不再依赖：

- Redis 作为图像检测队列中间件
- Celery 作为图像检测执行器
- 独立守护式 AI 服务监听脚本

## 已知限制

- `SingleImageMethod.py` 仍然较重，启动时会直接加载多组模型权重。
- LLM 相关路径保留在实现中，但目前更像“可选能力”而不是稳态依赖。
- 自动化测试已覆盖主链路和并发隔离逻辑，但未覆盖真实 GPU 权重推理。
- 仓库内仍保留部分历史训练代码和旧文档，阅读时应以 `local_infer.py` 与后端桥接层为准。
