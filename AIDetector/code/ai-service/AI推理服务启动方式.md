# AI 推理服务启动方式

图像鉴伪链路已经改为由后端直接调用本地 `local_infer.py`。

当前不再使用：

- 远程监听脚本
- 远程 GPU 服务
- 单独常驻的 AI 服务进程

## 当前入口

目录：

- `ai-forensics/code/ai-service/ai-service-code`

后端实际调用的脚本：

- `local_infer.py`

## 最小要求

- `AI_SERVICE_DIR` 指向 `ai-forensics/code/ai-service/ai-service-code`
- 当前 Python 环境具备该目录依赖
- 本地模型权重已经准备完成

## 说明

- 旧的 `main.py` 和 `trigger.py` 监听式流程已经移除
- 图像鉴伪结果通过标准输出序列化回传给后端
- 后端桥接层位于 `ai-forensics/code/backend/backend-code/core/call_figure_detection.py`
