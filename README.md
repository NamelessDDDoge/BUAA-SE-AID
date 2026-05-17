# BUAA-SE-AID

面向学术场景的 AI 鉴伪与人工复核协同系统。

## 开发者先看

当前项目的检测任务统一采用同一种语义：
- 前端可批量选择/上传资源
- 后端自动拆成多个单独检测任务
- 后端以受控并发方式执行这些任务
- 单任务详情页和报告继续保持单任务单资源视图

其中：
- 图像：多张图 -> 多个单独图像任务
- 论文：多篇论文 -> 多个单独论文任务
- Review：一篇论文 + 多篇 Review -> 多个单独 Review 任务

## 项目结构

```text
.
├── README.md
├── 图像检测并发改造设计说明.md
├── 图像检测联调与上线检查清单.md
├── 资源检测并发改造设计说明.md
├── 资源检测联调与上线检查清单.md
├── 架构共识.md
├── 需求文档4.21.md
└── AIDetector
    └── code
        ├── backend
        │   └── backend-code
        ├── frontend
        │   ├── frontend-user
        │   └── frontend-admin
        └── ai-service
            └── ai-service-code
```

## 核心代码位置

后端：
- `AIDetector/code/backend/backend-code/core/views/views_dectection.py`
- `AIDetector/code/backend/backend-code/core/services/orchestrators/image_task_orchestrator.py`
- `AIDetector/code/backend/backend-code/core/services/orchestrators/resource_task_orchestrator.py`
- `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_detection.py`
- `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_inference_client.py`

AI Service：
- `AIDetector/code/ai-service/ai-service-code/local_infer.py`
- `AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`
- `AIDetector/code/ai-service/ai-service-code/pipeline/pipeline_single_image.py`
- `AIDetector/code/ai-service/ai-service-code/method/SingleImageMethod.py`

前端：
- `AIDetector/code/frontend/frontend-user/src/pages/upload.vue`
- `AIDetector/code/frontend/frontend-user/src/features/results/PaperResultView.vue`
- `AIDetector/code/frontend/frontend-user/src/features/results/ReviewResultView.vue`

## 当前运行口径

建议使用：
- Python 环境：`se`
- 后端本地数据库模式：`DATABASE_MODE=local`

关键配置项：
- `IMAGE_TASK_MAX_WORKERS`
- `RESOURCE_TASK_MAX_WORKERS`
- `AI_REMOTE_INFER_URL`
- `AI_REMOTE_INFER_TIMEOUT`
- `AI_REMOTE_INFER_TOKEN`
- `AI_REMOTE_INFER_MAX_CONCURRENCY`
- `AI_SERVICE_PYTHON`

## 常用命令

后端测试：

```bash
cd AIDetector/code/backend/backend-code
env DATABASE_MODE=local AI_REMOTE_INFER_URL= AI_REMOTE_INFER_TOKEN= /root/miniconda3/envs/se/bin/python manage.py test
```

用户前端构建：

```bash
cd AIDetector/code/frontend/frontend-user
npm run build
```

## 文档入口

图像检测：
- [图像检测并发改造设计说明](./图像检测并发改造设计说明.md)
- [图像检测联调与上线检查清单](./图像检测联调与上线检查清单.md)

资源检测：
- [资源检测并发改造设计说明](./资源检测并发改造设计说明.md)
- [资源检测联调与上线检查清单](./资源检测联调与上线检查清单.md)

部署：
- [远程更新清单](./远程更新清单.md)

补充资料：
- [AIDetector/code/ai-service/AI推理服务启动方式.md](./AIDetector/code/ai-service/AI推理服务启动方式.md)
- [架构共识](./架构共识.md)
- [需求文档4.21.md](./需求文档4.21.md)
