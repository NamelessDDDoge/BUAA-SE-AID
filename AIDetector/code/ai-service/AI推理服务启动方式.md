# AI 推理服务启动方式

本文档说明当前项目的两种图像推理运行方式：

1. 服务器本地推理
2. 服务器业务 + 笔记本 GPU 远程推理

如果服务器没有显卡，而你的笔记本有显卡，推荐使用第 2 种方式。

## 当前代码支持的两种模式

### 模式 A：服务器本地推理

后端直接在服务器上启动：

- `AIDetector/code/ai-service/ai-service-code/local_infer.py`

适用于：

- 服务器本身有可用 GPU
- 或只做轻量 CPU 调试

### 模式 B：远程 GPU 推理

后端仍然运行在服务器上，但图像推理会改为调用一个 HTTP 推理桥：

- 服务器后端读取 `img.zip` 和 `data.json`
- 后端把它们 POST 到 `AI_REMOTE_INFER_URL`
- 笔记本上的 `gpu_infer_service.py` 收到请求后，在本机调用 `local_infer.py`
- 推理结果返回给服务器后端，后端照常落库和出报告

适用于：

- 服务器没有显卡
- 笔记本有显卡
- 希望前后端、数据库都部署在服务器

## 推荐部署拓扑

推荐链路如下：

```text
前端 -> 服务器 Nginx -> 服务器 Django
                         |
                         v
                 AI_REMOTE_INFER_URL
                         |
                  127.0.0.1:18080
                         |
                 反向 SSH 隧道 -R
                         |
                  笔记本 127.0.0.1:18080
                         |
                  gpu_infer_service.py
                         |
                      local_infer.py
```

这里推荐使用反向 SSH 隧道，而不是要求服务器直接访问笔记本公网 IP。

## 方案一：服务器本地推理

### 1. 准备环境

确保服务器安装了：

- Python 环境
- `AIDetector/code/backend/backend-code/requirements.txt` 依赖
- AI 权重文件

### 2. 配置后端

在后端 `.env` 中配置：

```env
AI_SERVICE_DIR=/root/BUAA-SE-AID/AIDetector/code/ai-service/ai-service-code
AI_SERVICE_PYTHON=/path/to/python
AI_REMOTE_INFER_URL=
```

这里不要设置 `AI_REMOTE_INFER_URL`。

### 3. 启动

只启动后端即可，图像检测时后端会自动拉起：

- `local_infer.py`

## 方案二：服务器业务 + 笔记本 GPU 推理

这是推荐方案。

### 第 1 步：在笔记本准备 AI 推理环境

工作目录：

- `AIDetector/code/ai-service/ai-service-code`

需要准备：

- CUDA / 显卡驱动
- Python 环境
- `local_infer.py` 依赖
- 模型权重

先在笔记本本地验证：

```bash
python local_infer.py
```

如果没有准备 `img.zip` / `data.json`，这一步不一定能完整跑通，但至少要保证依赖导入和模型环境没有明显问题。

### 第 2 步：在笔记本启动 GPU 推理服务

新增的服务脚本是：

- `AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`

最小启动方式：

```bash
cd /path/to/AIDetector/code/ai-service/ai-service-code
export AI_SERVICE_PYTHON=/path/to/python
export AI_REMOTE_INFER_HOST=127.0.0.1
export AI_REMOTE_INFER_PORT=18080
export AI_REMOTE_INFER_TOKEN=replace-with-a-long-random-string
python gpu_infer_service.py
```

服务健康检查：

```bash
curl http://127.0.0.1:18080/health
```

### 第 3 步：建立反向 SSH 隧道

在笔记本执行：

```bash
ssh -N -R 127.0.0.1:18080:127.0.0.1:18080 <server-user>@<server-host>
```

更推荐长期运行版本：

```bash
autossh -M 0 -N -R 127.0.0.1:18080:127.0.0.1:18080 <server-user>@<server-host>
```

效果是：

- 服务器访问 `127.0.0.1:18080`
- 实际转发到笔记本本地的 `127.0.0.1:18080`

### 第 4 步：在服务器配置后端

后端 `.env` 示例：

```env
AI_SERVICE_DIR=/root/BUAA-SE-AID/AIDetector/code/ai-service/ai-service-code
AI_SERVICE_PYTHON=/path/to/server/python
AI_REMOTE_INFER_URL=http://127.0.0.1:18080/infer
AI_REMOTE_INFER_TIMEOUT=1800
AI_REMOTE_INFER_TOKEN=replace-with-a-long-random-string
```

说明：

- 只要设置了 `AI_REMOTE_INFER_URL`，后端就会优先走远程推理
- 不再在服务器本机启动 `local_infer.py`

### 第 5 步：重启后端

重启 Django / uWSGI / Gunicorn 后生效。

## 可选：用 systemd 常驻笔记本服务

如果笔记本是 Linux，推荐把 GPU 推理服务和反向 SSH 隧道都做成 `systemd` 服务。

### 1. `gpu-infer.service`

示例：

```ini
[Unit]
Description=BUAA GPU Infer Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/path/to/AIDetector/code/ai-service/ai-service-code
Environment=AI_SERVICE_PYTHON=/path/to/python
Environment=AI_REMOTE_INFER_HOST=127.0.0.1
Environment=AI_REMOTE_INFER_PORT=18080
Environment=AI_REMOTE_INFER_TOKEN=replace-with-a-long-random-string
ExecStart=/path/to/python /path/to/AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. `gpu-infer-tunnel.service`

示例：

```ini
[Unit]
Description=Reverse SSH Tunnel For BUAA GPU Infer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/autossh -M 0 -N -R 127.0.0.1:18080:127.0.0.1:18080 <server-user>@<server-host>
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用方式：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gpu-infer.service
sudo systemctl enable --now gpu-infer-tunnel.service
```

## 验证步骤

### 1. 检查笔记本服务

在笔记本：

```bash
curl http://127.0.0.1:18080/health
```

### 2. 检查服务器是否能穿透到笔记本

在服务器：

```bash
curl http://127.0.0.1:18080/health
```

如果反向隧道正常，这里也应返回健康检查 JSON。

### 3. 从前端提交一张测试图片

提交一张图片检测任务，观察：

- Django 日志
- 笔记本 `gpu_infer_service.py` 日志

若正常，应出现：

- 后端任务进入 `completed`
- 检测结果和报告正常生成

## 并发与限制

当前实现有一个重要限制：

- `local_infer.py` 及其下游 pipeline 会使用固定缓存目录和固定输入文件名
- 因此不适合同时并发跑多个图像推理请求

为避免相互覆盖，`gpu_infer_service.py` 默认对推理请求加了串行锁，一次只处理一个请求。

这意味着：

- 单任务稳定
- 多任务并发时会排队

对于课程项目、演示环境、轻量内部使用，这通常是可接受的。

## 安全建议

建议至少这样做：

- `gpu_infer_service.py` 只监听 `127.0.0.1`
- 仅通过反向 SSH 隧道暴露给服务器
- 设置 `AI_REMOTE_INFER_TOKEN`
- 不要把笔记本推理端口直接暴露到公网

## 常见问题

### 1. 服务器报 401 unauthorized

说明：

- 服务器配置的 `AI_REMOTE_INFER_TOKEN`
- 和笔记本服务启动时的 `AI_REMOTE_INFER_TOKEN`

不一致。

### 2. 服务器报连接失败

检查：

- 笔记本 `gpu_infer_service.py` 是否还在运行
- 反向 SSH 隧道是否仍然在线
- 服务器上 `curl http://127.0.0.1:18080/health` 是否成功

### 3. 推理很慢或首次很慢

这是正常的。当前 pipeline 初始化时会加载多组模型权重，首次启动成本较高。

### 4. 论文检测也失败了

论文任务中的图片检测也复用这条图像检测链路。如果远程 GPU 不可用，论文里的文本分析可能还能继续，但图片检测部分会失败。

## 相关文件

- 后端桥接：
  - `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_inference_client.py`
- 笔记本推理服务：
  - `AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`
- 本地图像推理入口：
  - `AIDetector/code/ai-service/ai-service-code/local_infer.py`
