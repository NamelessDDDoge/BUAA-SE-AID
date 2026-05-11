# AI 推理服务启动方式

本文档只说明一种推荐用法：

- 前后端、数据库都跑在服务器
- 图像推理跑在你本地笔记本 GPU

适用场景：

- 服务器没有显卡
- 笔记本有显卡
- 需要让服务器上的后端调用笔记本本地显卡完成推理

---

## 一、整体流程

最终链路如下：

```text
前端 -> 服务器 Django -> 服务器 127.0.0.1:18080
                         |
                         v
                反向 SSH 隧道
                         |
                         v
                笔记本 127.0.0.1:18080
                         |
                         v
               gpu_infer_service.py
                         |
                         v
                   local_infer.py
```

意思是：

1. 服务器后端收到图片检测请求
2. 后端把数据发到 `AI_REMOTE_INFER_URL`
3. 这个地址通过 SSH 隧道转发到你的笔记本
4. 笔记本本地用 GPU 完成推理
5. 结果再返回服务器

---

## 二、你需要准备什么

### 服务器

- 已经跑起来的 Django 后端
- 后端 `.env` 可修改
- 能正常访问本地 `127.0.0.1`

### 笔记本

- 有 NVIDIA GPU
- 已安装 CUDA / 显卡驱动
- 已安装 Python 环境
- 已有本仓库代码，至少有：
  - `AIDetector/code/ai-service/ai-service-code`
- 已准备模型依赖和权重

---

## 三、笔记本端怎么启动

### 第 1 步：进入 AI 服务目录

```bash
cd AIDetector/code/ai-service/ai-service-code
```

### 第 2 步：启动 GPU 推理服务
下面这些配置可以直接写到 AIDetector/code/backend/backend-code/.env 中

Linux / macOS：

```bash
export AI_SERVICE_PYTHON=/你的python路径（例如/root/miniconda3/envs/se/bin/python）
export AI_REMOTE_INFER_HOST=127.0.0.1
export AI_REMOTE_INFER_PORT=18080
export AI_REMOTE_INFER_TOKEN=你自己设置的随机串
python gpu_infer_service.py
```

Windows PowerShell：

```powershell
$env:AI_SERVICE_PYTHON="你的python路径"
$env:AI_REMOTE_INFER_HOST="127.0.0.1"
$env:AI_REMOTE_INFER_PORT="18080"
$env:AI_REMOTE_INFER_TOKEN="你自己设置的随机串"
python .\gpu_infer_service.py
```

### 第 3 步：验证笔记本服务是否起来

```bash
curl http://127.0.0.1:18080/health
```

如果成功，应该返回 JSON。

---

## 四、建立 SSH 反向隧道

在笔记本再开一个终端，执行：

```bash
ssh -N -R 127.0.0.1:18080:127.0.0.1:18080 root@你的服务器公网IP
```

例如：

```bash
ssh -N -R 127.0.0.1:18080:127.0.0.1:18080 root@122.9.32.72
```

### 正常现象

- 输入密码后没有任何输出
- 终端像“卡住”一样
- 光标不返回

这是正常的，说明 SSH 正在维持隧道。

不要关闭这个终端。

---

## 五、服务器端怎么配置

修改服务器后端实际生效的 `.env`：

- `AIDetector/code/backend/backend-code/.env`

至少加入这几项：

```env
AI_REMOTE_INFER_URL=http://127.0.0.1:18080/infer
AI_REMOTE_INFER_TIMEOUT=1800
AI_REMOTE_INFER_TOKEN=和笔记本完全一致
```

建议同时确认：

```env
AI_SERVICE_DIR=/root/BUAA-SE-AID/AIDetector/code/ai-service/ai-service-code
AI_SERVICE_PYTHON=/root/miniconda3/envs/se/bin/python
```

说明：

- 只要设置了 `AI_REMOTE_INFER_URL`
- 后端就不会再走服务器本地推理
- 而是把请求发给你笔记本上的 GPU 服务

---

## 六、服务器端怎么验证隧道是否打通

修改 `.env` 后，重启后端。

然后在服务器执行：

```bash
curl http://127.0.0.1:18080/health
```

如果返回 JSON，说明以下几件事都对了：

- 笔记本上的 `gpu_infer_service.py` 正常运行
- SSH 反向隧道正常
- 服务器已经能访问你笔记本本地服务

如果这一步不通，不要去前端点检测，先解决这里。

---

## 七、第一次联调怎么做

确认下面 3 件事都成立：

1. 笔记本本地：

```bash
curl http://127.0.0.1:18080/health
```

2. 服务器本地：

```bash
curl http://127.0.0.1:18080/health
```

3. 后端已重启并读取到新 `.env`

然后再去前端做一次图片检测：

1. 上传一张测试图片
2. 提交检测任务
3. 同时观察：
   - 服务器 Django 日志
   - 笔记本 `gpu_infer_service.py` 终端日志

如果成功，你会看到：

- 服务器收到任务
- 笔记本收到 `/infer` 请求
- 本地开始推理
- 结果返回服务器
- 前端能看到检测结果

---

## 八、常见错误

### 1. 服务器报 401 unauthorized

原因：

- 服务器 `.env` 里的 `AI_REMOTE_INFER_TOKEN`
- 和笔记本启动时设置的 `AI_REMOTE_INFER_TOKEN`

不一致。

### 2. 服务器报连接失败

先检查：

```bash
curl http://127.0.0.1:18080/health
```

如果服务器本地都不通，问题通常是：

- 笔记本 `gpu_infer_service.py` 没启动
- SSH 隧道断了
- 笔记本把终端关了

### 3. 报 `Remote AI inference request failed with HTTP 500`

说明：

- 服务器到笔记本的链路已经通了
- 但笔记本本地 `local_infer.py` 启动失败

这时要看笔记本终端里的完整 traceback。

最常见原因：

- 缺 Python 包
- 缺模型权重
- 本地环境不完整

### 4. 第一次推理很慢

这是正常的。

原因：

- `local_infer.py` 首次启动时会加载模型权重

### 5. 同时多个任务很慢

当前实现是串行处理的，一次只处理一个推理请求。

这是为了避免本地图像缓存和临时文件互相覆盖。

---

## 九、最短操作清单

如果你只想照着做，按下面顺序执行：

### 笔记本

1. 启动 GPU 推理服务
2. 本地 `curl 127.0.0.1:18080/health`
3. 建立 SSH 反向隧道

### 服务器

4. 修改 `.env`：
   - `AI_REMOTE_INFER_URL`
   - `AI_REMOTE_INFER_TOKEN`
5. 重启 Django 后端
6. 服务器执行：

```bash
curl http://127.0.0.1:18080/health
```

### 前端

7. 上传测试图片并提交检测

---

## 十、相关文件

- 服务器后端桥接：
  - `AIDetector/code/backend/backend-code/core/services/capabilities/image/local_inference_client.py`
- 笔记本推理服务：
  - `AIDetector/code/ai-service/ai-service-code/gpu_infer_service.py`
- 本地图像推理入口：
  - `AIDetector/code/ai-service/ai-service-code/local_infer.py`
