# AI Service 实现说明

本文档介绍当前仓库中 AI Service 的真实实现和它与后端的对接方式。

当前 AI Service 不是独立部署的 HTTP 服务，也不是常驻守护进程。它的实际角色是一个"由 Django 后端按需拉起的本地推理脚本集合"。

## 目录结构

```text
AIDetector/code/ai-service
├── README.md
├── AI推理服务启动方式.md
└── ai-service-code
    ├── local_infer.py          # 实际入口脚本
    ├── pipeline
    │   ├── pipline_base.py
    │   └── pipeline_single_image.py  # 单图检测编排
    └── method
        ├── SingleImageMethod.py       # 核心聚合层
        ├── Config.py                 # 方法开关配置
        ├── urn/                      # URN 模型推理（5个权重）
        └── llm/                      # LLM 推理（DTE-FDM + MFLM 两阶段）
```

## 当前真实入口

后端实际启动的入口脚本是：

- `ai-service-code/local_infer.py`

它的职责只有三件事：

1. 从共享目录读取 `img.zip` 和 `data.json`。
2. 构造 `PipelineSingleImage` 并执行推理。
3. 把结果序列化后打印到标准输出，供后端读取。

这里没有 Web Server，也没有消息队列消费者。

## 与后端的对接关系

后端桥接代码在：

- `AIDetector/code/backend/backend-code/core/call_figure_detection.py`

它的执行方式是：

1. 把后端生成的图片输入整理到共享目录。
2. 设置环境变量和临时目录。
3. 使用 `subprocess.run(...)` 直接拉起 `local_infer.py`。
4. 从 stdout 中查找 `start results` 标记。
5. 读取下一行 base64 文本并反序列化为 Python 对象。

因此，AI Service 当前本质上是"本地 Python 子进程推理"。

## 输入格式

### 图片输入

后端会把一批图片打成 `img.zip`。`local_infer.py` 会遍历 zip 根目录中的图片文件，支持：

- `.png`
- `.jpg`
- `.jpeg`
- `.bmp`
- `.gif`

每张图会被读取成 `numpy.ndarray`。

### 参数输入

后端同时生成 `data.json`，当前主要参数为：

- `cmd_block_size`：CMD 方法的块大小（默认 64）
- `urn_k`：URN 系列方法的置信度阈值（默认 0.3）
- `if_use_llm`：是否启用 LLM 推理（默认 False）
- `method_switches`：子任务开关映射（可选，例如 `{"ela": true, "exif": false}`），未传入时使用 `Config.py` 中的默认值

这些参数会直接写入 `SingleImageMethod.method_parameters`。

## 内部执行链路

当前链路为：

1. `local_infer.py`
2. `PipelineSingleImage`
3. `SingleImageMethod`
4. 各个具体方法

### `PipelineSingleImage`

文件：

- `ai-service-code/pipeline/pipeline_single_image.py`

当前后端调用的是 `run_multi_images(...)`，不是 `run(...)`。

它会：

1. 清理并重建缓存目录 `~/.codex/memories/ai_image_cache`
2. 把每张输入图片落盘成 `image_0.jpg`、`image_1.jpg` 等文件
3. 遍历 `SingleImageMethod.get_methods()` 返回的方法列表
4. 将每个方法的结果追加到 `self.results`

当前 `results` 是"按方法组织"的结构，而不是"按图片组织"的结构。后端会再按索引拆回每张图对应的结果。

### `SingleImageMethod`

文件：

- `ai-service-code/method/SingleImageMethod.py`

这个类是当前图像鉴伪的核心聚合层。

初始化时会立即加载多组 URN 权重：

- `weight/Coarse_v2.pkl`
- `weight/blurring.pkl`
- `weight/brute_force.pkl`
- `weight/contrast.pkl`
- `weight/inpainting.pkl`

这意味着：

- AI Service 启动不是轻量操作
- 权重缺失会直接影响启动和推理
- 首次调用的耗时主要集中在这里

## 当前方法组成（共 9 个子检测任务）

`get_methods()` 当前返回顺序如下：

1. `llm_method`
2. `ela_method`
3. `exif_method`
4. `cmd_method`
5. `urn_coarse_v2_method`
6. `urn_blur_method`
7. `urn_brute_method`
8. `urn_contrast_method`
9. `urn_inpating_method`

其中 `urn_*` 五个方法在结果层面被后端映射为 5 个子方法名：

| 后端子方法名 | 含义 | URN 权重文件 |
|---|---|---|
| `splicing`（拼接） | 检测图片中是否存在拼接/合成区域 | `Coarse_v2.pkl` |
| `blurring`（模糊） | 检测是否存在模糊处理过的区域（常用于隐藏拼接痕迹） | `blurring.pkl` |
| `bruteforce`（暴力攻击） | 检测是否经过极端处理（如超分辨率重建等暴力操作） | `brute_force.pkl` |
| `contrast`（对比度） | 检测局部对比度异常（拼接区域常见） | `contrast.pkl` |
| `inpainting`（填充） | 检测是否存在 AI 填充/生成区域 | `inpainting.pkl` |

---

### 1. LLM 方法（`llm`）

- **开关名称**：`llm`
- **中文意译**：大语言模型多模态 AI 鉴别
- **技术原理**：通过 DTE-FDM 提取图像特征，再经 MFLM 多阶段推理，综合判断图像是否由 AI 生成或经过篡改
- **启用条件**：`if_use_llm` 为 True 时才执行
- **依赖**：额外 conda 环境 `/root/miniconda3/envs/llm`，依赖 `method/llm` 下的权重 `fakeshield-v1-22b`
- **注意**：当前实现依赖外部研究型环境，稳定性弱于非 LLM 路径；LLM 方法消耗组织额度

---

### 2. ELA 方法（`ela`）

- **开关名称**：`ela`
- **中文意译**：误差级分析（Error Level Analysis）
- **技术原理**：将图像以 JPEG 质量 90 重新保存，再与原图做差分，得到每个像素的误差级。拼接区域由于经历过不同的压缩级别，误差会显著偏高，在 mask 中呈现高亮。输出灰度误差 mask，亮处为可疑区域。
- **参数**：无额外参数
- **输出**：灰度 mask，像素值越高越可疑

---

### 3. EXIF 方法（`exif`）

- **开关名称**：`exif`
- **中文意译**：图片元数据篡改检测
- **技术原理**：读取图片 EXIF 元数据，检查以下可疑项：
  - `Software` 字段是否包含 "Photoshop"（使用了 Photoshop 修改）
  - `DateTimeOriginal` 与 `DateTime` 是否不一致（修改了拍摄/制作时间）
- **输出**：文本型可疑项列表，无则为 None
- **注意**：EXIF 字段可以被刻意清除，此方法对已清除元数据的图片无效

---

### 4. CMD 方法（`cmd`）

- **开关名称**：`cmd`
- **中文意译**：复制移动伪造检测（Copy-Move Detection）
- **技术原理**：对灰度图进行分块，使用模板匹配（match_template）在整图中搜索与当前块相似度 ≥ 0.9 的其他块。如果两个相似块之间的距离超过块大小，说明存在复制移动操作（某区域被复制粘贴到另一区域）。输出二值 mask，可疑区域标记为白色。
- **参数**：`cmd_block_size` 控制块大小（默认 64），越小越精细但越慢
- **输出**：二值 mask，白色区域为疑似复制移动区域

---

### 5. URN 拼接检测（`urn_coarse_v2`）

- **开关名称**：`urn_coarse_v2`
- **中文意译**：拼接检测（高精度卷积网络）
- **技术原理**：加载 URN 权重 `Coarse_v2.pkl`，输入图片经卷积网络推理，输出篡改区域的概率热力图（splicing mask）。网络学习到拼接边缘的噪声不一致性和纹理异常。
- **参数**：`urn_k` 概率阈值（默认 0.3），高于此值判定为可疑
- **输出**：概率 mask 和概率值（0~1）

---

### 6. URN 模糊检测（`urn_blurring`）

- **开关名称**：`urn_blurring`
- **中文意译**：模糊处理检测（检测是否有区域被模糊化以隐藏拼接痕迹）
- **技术原理**：加载 URN 权重 `blurring.pkl`，网络学习图像局部模糊程度分布，输出模糊区域的 mask。篡改者常对拼接边缘做模糊处理以减少视觉违和感。
- **参数**：`urn_k` 概率阈值（默认 0.3）
- **输出**：概率 mask 和概率值（0~1）

---

### 7. URN 暴力攻击检测（`urn_brute_force`）

- **开关名称**：`urn_brute_force`
- **中文意译**：极端处理检测（检测超分辨率、强力去噪等极端操作）
- **技术原理**：加载 URN 权重 `brute_force.pkl`，检测图片是否经过超分辨率重建、强力去噪等"暴力"图像处理操作。这类操作会在局部引入特征异常。
- **参数**：`urn_k` 概率阈值（默认 0.3）
- **输出**：概率 mask 和概率值（0~1）

---

### 8. URN 对比度检测（`urn_contrast`）

- **开关名称**：`urn_contrast`
- **中文意译**：对比度异常检测（检测局部对比度不一致的拼接区域）
- **技术原理**：加载 URN 权重 `contrast.pkl`，检测图片局部对比度分布是否一致。拼接区域由于来源不同，对比度统计通常存在差异。
- **参数**：`urn_k` 概率阈值（默认 0.3）
- **输出**：概率 mask 和概率值（0~1）

---

### 9. URN 填充检测（`urn_inpainting`）

- **开关名称**：`urn_inpainting`
- **中文意译**：AI 填充/生成区域检测（检测是否包含 AI 生成内容）
- **技术原理**：加载 URN 权重 `inpainting.pkl`，检测图片中是否存在 AI 生成或 AI 填充的区域（如 AI 补全、局部生成等操作留下的痕迹）。
- **参数**：`urn_k` 概率阈值（默认 0.3）
- **输出**：概率 mask 和概率值（0~1）

---

## 子任务开关配置（`Config.py`）

文件：`ai-service-code/method/Config.py`

```python
SINGLE_IMAGE_METHOD_SWITCHES = {
    "llm": False,            # 大语言模型多模态 AI 鉴别
    "ela": False,            # 误差级分析（ELA）
    "exif": False,           # EXIF 元数据篡改检测
    "cmd": False,            # 复制移动伪造检测（CMD）
    "urn_coarse_v2": True,   # 拼接检测（高精度卷积网络）
    "urn_blurring": False,   # 模糊处理检测
    "urn_brute_force": False,# 极端处理检测
    "urn_contrast": False,   # 对比度异常检测
    "urn_inpainting": False, # AI 填充/生成区域检测
}
```

如需在后端提交检测任务时动态控制哪些子任务启用，可以通过 `data.json` 传入 `method_switches` 字段（JSON 对象），覆盖默认值。传入格式例如：

```json
{
  "cmd_block_size": 64,
  "urn_k": 0.3,
  "if_use_llm": false,
  "method_switches": {
    "ela": true,
    "exif": true,
    "cmd": true,
    "urn_coarse_v2": true
  }
}
```

## 返回数据结构

AI Service 最终返回的是一个 Python 对象，之后经 `pickle.dumps(...)` 和 `base64.b64encode(...)` 输出。

顶层结构是一个列表，每一项形如 `(method_name, method_results)`，顺序与 `get_methods()` 一致：

```python
[
    ("llm", [...]),          # 第0项
    ("ela", [...]),          # 第1项
    ("exif", [...]),         # 第2项
    ("cmd", [...]),          # 第3项
    ("urn_coarse_v2", [...]),# 第4项 → 后端映射为 splicing
    ("urn_blurring", [...]), # 第5项 → 后端映射为 blurring
    ("urn_brute_force", [...]), # 第6项 → 后端映射为 bruteforce
    ("urn_contrast", [...]),# 第7项 → 后端映射为 contrast
    ("urn_inpainting", [...]),  # 第8项 → 后端映射为 inpainting
]
```

后端解析逻辑在：

- `AIDetector/code/backend/backend-code/core/local_detection.py`

其中：

- `LLM` 结果会拆成 `llm_text` 和 `llm_img`
- `ELA` 会变成 `DetectionResult.ela_image`
- `EXIF` 会映射为真假布尔标记（`exif_photoshop` / `exif_time_modified`）
- URN 5项结果会转成 5 个 `SubDetectionResult`（method 分别为 `splicing`/`blurring`/`bruteforce`/`contrast`/`inpainting`）

总体真假判定规则：

- 任一子方法概率大于 `0.5`，或 EXIF 有可疑项 → 整张图标记为疑似造假

## 运行时目录

当前实现会使用这些目录：

- `AI_SERVICE_TEST_DIR`：共享输入输出目录
- `AI_SERVICE_TMP_DIR`：临时目录
- `AI_SERVICE_TORCH_HOME`：Torch 缓存目录
- `~/.codex/memories/ai_image_cache`：pipeline 中间图片缓存

`local_infer.py` 会主动覆盖：

- `TMP`、`TEMP`、`TMPDIR`、`TORCH_HOME`

## 当前真实生效的环境变量

- `AI_SERVICE_DIR`：AI Service 根目录
- `AI_SERVICE_ENTRYPOINT`：入口脚本路径
- `AI_SERVICE_PYTHON`：启动脚本使用的 Python
- `AI_SERVICE_TEST_DIR`：共享输入输出目录
- `AI_SERVICE_TMP_DIR`：临时目录
- `AI_SERVICE_TORCH_HOME`：Torch 缓存目录

如果只配一个变量，优先保证 `AI_SERVICE_DIR` 正确；如果后端与 AI Service 不在同一解释器环境，再补 `AI_SERVICE_PYTHON`。

## 当前实现的特点

### 优点

- 部署简单，不需要额外服务编排
- 后端与 AI 推理链路清晰，排查更直接
- 图像检测结果可以直接落成数据库记录和报告文件

### 限制

- 启动成本高，尤其是 URN 权重加载阶段
- LLM 路径依赖额外环境，稳定性明显弱于非 LLM 路径
- `PipelineSingleImage` 的结果结构较原始，强依赖后端解析顺序
- 目录中同时保留了训练代码、研究代码和现网调用代码，阅读时容易混淆

## 阅读建议

如果要快速理解当前 AI Service，建议按这个顺序阅读：

1. `AIDetector/code/backend/backend-code/core/views/views_dectection.py`
2. `AIDetector/code/backend/backend-code/core/local_detection.py`
3. `AIDetector/code/backend/backend-code/core/call_figure_detection.py`
4. `AIDetector/code/ai-service/ai-service-code/local_infer.py`
5. `AIDetector/code/ai-service/ai-service-code/pipeline/pipeline_single_image.py`
6. `AIDetector/code/ai-service/ai-service-code/method/SingleImageMethod.py`

这样能先看现网调用链，再下钻到算法实现，避免被历史训练目录带偏。
