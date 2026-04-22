# 前后端主导的三路检测重构执行计划

## 1. 这份计划是干什么的

这不是一份“方向性想法”文档，而是一份可以直接执行的重构说明。

目标是让一个从来没看过这个项目的人，也能在不依赖历史上下文的情况下，理解下面几件事：

- 这个项目当前要交付什么
- 为什么必须重构，而不是继续在旧代码上打补丁
- 重构边界在哪里，哪些目录可以动，哪些绝对不能动
- 图像检测、论文检测、同行评审检测三条链路最终要长成什么样
- 每个阶段具体改哪些文件、补哪些测试、怎么验证成功
- 每个阶段完成后为什么要立刻提交 git，并尝试 push

本计划的设计依据只有两类：

- 当前执行任务本身
- 根目录 `架构共识.md`

其他旧文档、旧注释、旧页面文案，都只能作为“当前现状输入”，不能当成目标规范。

---

## 2. 项目目标

当前项目要统一承载三类检测任务：

1. 图像检测
2. 全文论文检测
3. 同行评审检测

三类任务不是三套独立系统，而是同一个系统下的三种业务流程。重构后的目标不是“把功能做更多”，而是先把系统骨架拉直，保证：

- 图像检测现有可用能力不被破坏
- 论文检测不再停留在占位逻辑，而是形成最小闭环
- 同行评审检测不再混在旧 review 逻辑里，而是形成独立、可读、可测的任务流
- 前端能按任务类型组织页面和数据，而不是把所有逻辑硬塞进单页
- 后端结果结构不再继续堆进 JSON 字段里
- 后续模型管理、事件日志、管理端统计能在现有基础上继续长出来

一句话概括：

> 保持接口外观尽量不变，把内部实现从“视图里塞满业务逻辑”重构成“接口层 + 资源层 + 编排层 + 能力层 + 存储层”的稳定结构。

---

## 3. 当前现状

### 3.1 当前真正生效的核心代码在哪里

本轮主要工作区只有三个：

- `AIDetector/code/backend/backend-code`
- `AIDetector/code/frontend/frontend-user`
- `AIDetector/code/frontend/frontend-admin`

后端当前真正承载核心逻辑的集中区域是：

```text
AIDetector/code/backend/backend-code/core
├─ models.py
├─ tasks.py
├─ local_detection.py
├─ call_figure_detection.py
├─ utils/report_generator.py
└─ views/
   ├─ views_imageupload.py
   ├─ views_dectection.py
   └─ views_review.py
```

用户端当前主要入口是：

```text
AIDetector/code/frontend/frontend-user/src
├─ pages/upload.vue
├─ pages/history.vue
├─ pages/step/[id].vue
└─ api/publisher.ts
```

管理端当前主要入口是：

```text
AIDetector/code/frontend/frontend-admin/src
├─ pages/files.vue
├─ pages/reviews.vue
├─ pages/logs.vue
├─ pages/analytics.vue
└─ api/*.ts
```

### 3.2 当前问题是什么

当前系统最大的问题不是“没有功能”，而是“功能入口已经有了，但职责边界严重混乱”。

具体表现：

- `views_imageupload.py` 里同时负责参数校验、文件落盘、图片抽取、资源类型判断、关联关系处理
- `views_dectection.py` 里同时负责图像检测任务创建、论文任务创建、状态聚合、结果序列化、报告下载
- `tasks.py` 里的论文检测还是直接写死外部请求和分段逻辑，属于明显占位实现
- 论文和评审结果继续塞进 `DetectionTask.text_detection_results`，没有结构化持久层
- 前端页面已经开始支持三类任务，但数据组织和 API 模块仍是图像检测时代的混合风格
- 管理端数据面板偏图像中心，不具备稳定的任务类型视角

如果继续在这个结构上加功能，结果只会是：

- 更难读
- 更难测
- 更难定位故障
- 更难扩展论文和评审闭环

---

## 4. 重构原则

### 4.0 来自《架构共识.md》的固定前提

以下内容已经在 `架构共识.md` 中确认，不属于本次执行时可以随意变更的开放问题。它们必须被视为本计划的硬约束：

1. 系统必须按五层组织：
   - 接口层
   - 资源层
   - 编排层
   - 能力层
   - 存储层
2. 图像检测、论文检测、同行评审检测共享同一套架构，不做三套平行系统。
3. 图像检测能力必须被论文检测直接复用，论文检测不得另写一套图像鉴伪逻辑。
4. 文本检测能力必须同时服务论文检测和同行评审检测，不能拆出两套彼此独立的文本检测实现。
5. 大模型调用能力必须统一纳入能力层/集成层，不能散落在视图、任务函数和临时脚本中。
6. 论文检测最小闭环必须包含：
   - 文件预处理
   - 段落级文本检测
   - 论文内图像检测
   - 可疑段落解释
   - 参考文献存在性与相关性检查
7. 同行评审检测最小闭环必须包含：
   - 原论文与 Review 双输入
   - review 文本预处理
   - review 段落级文本检测
   - review 与原论文逐段相关性分析
8. 管理端日志最终必须统一成事件模型，不能继续只围绕图像上传和人工审核。
9. 管理端统计视角最终必须能覆盖 `image/paper/review` 三类任务。
10. 模型接入设计必须预留多协议扩展，结构上至少允许：
    - OpenAI 风格接口
    - Anthropic 风格接口
    - 自定义 HTTP API 接口
11. 模型配置与默认模型选择必须解耦：
    - 一套配置维护所有模型
    - 每个功能独立选择默认模型

### 4.1 原则一：接口尽量稳定，内部可以重排

本轮不是 API 改版。已有前端和管理端已经接入的接口，优先保持路径不变：

- `/api/upload/`
- `/api/detection/submit/`
- `/api/resource-task/create/`
- `/api/detection-task/<id>/status/`
- `/api/paper-results/<id>/`

允许做的事：

- 让视图变成薄适配层
- 在视图后面新增服务层和编排层
- 为结果读取新增补充型接口

不优先做的事：

- 改现有路径命名
- 新建一套平行 API
- 重做前后端路由体系

### 4.2 原则二：先锁行为，再重构

凡是要抽逻辑、改结构、搬代码，先补回归测试。

顺序固定：

1. 先补/拆测试，锁住现有行为
2. 再搬逻辑
3. 每个 slice 完成后立刻验证
4. 验证成功后立刻 git commit，并尝试 git push

### 4.3 原则三：优先复用现有图像能力

论文检测中的图片分析必须复用现有图像检测链路，不能重新发明一套图像鉴伪实现。

也就是说：

- `local_detection.py`
- `call_figure_detection.py`

这两块是现有“图像能力底座”，应该被 service 包起来复用，而不是被论文检测重复实现。

### 4.4 原则四：论文和评审共享文本能力

论文检测和同行评审检测都需要：

- 文本预处理
- 段落切分
- 段落检测
- LLM 分析

所以文本检测不能分别写两套。

### 4.5 原则五：不碰训练主干

下面这些目录本轮默认禁止修改：

- `AIDetector/code/ai-training/**`
- `AIDetector/code/ai-service/ai-service-code/method/urn/**`
- `AIDetector/code/ai-service/ai-service-code/method/llm/**`
- `AIDetector/code/ai-service/ai-service-code/pipeline/**`

只有在论文/评审本地入口无法通过后端 service 层解决时，才允许新增一个“很薄的适配入口”。

---

## 5. 这次重构的明确边界

### 5.1 可以改的范围

- 根目录跟踪文件：`plan.md`、`prd.json`、`progress.md`
- 后端：`AIDetector/code/backend/backend-code/**`
- 用户端：`AIDetector/code/frontend/frontend-user/**`
- 管理端：`AIDetector/code/frontend/frontend-admin/**`

### 5.2 不改的范围

- `AIDetector/code/ai-training/**`
- AI 服务里的训练/算法主体实现
- 现有前后端路由路径
- Django app 边界，不新拆 app

### 5.3 默认保留的兼容策略

- 老接口尽量继续可用
- 老视图保留入口，但逐步变薄
- `DetectionTask.text_detection_results` 在结果表拆分期间保留兼容
- 图像任务结果仍沿用 `ImageUpload` / `DetectionResult`

---

## 6. 目标架构

依据 `架构共识.md`，本轮后端目标架构固定为五层：

```text
接口层 -> 资源层 -> 编排层 -> 能力层 -> 存储层
```

### 6.1 接口层

位置：

- `core/views/views_imageupload.py`
- `core/views/views_dectection.py`
- `core/views/views_review.py`

职责：

- 接收请求
- 调参数校验和权限校验
- 调用 service / orchestrator
- 返回前端可消费的数据

不再负责：

- 文件预处理细节
- 任务编排
- 外部 API 直调
- 结果拼装细节

### 6.2 资源层

建议目录：

```text
core/services/resources/
```

职责：

- 文件落盘
- 图像抽取
- 文本提取
- 段落切分
- 引文粗提取
- 建立论文文件与评审文件的关联

### 6.3 编排层

建议目录：

```text
core/services/orchestrators/
```

职责：

- 决定某类任务如何分步骤执行
- 管理状态推进
- 处理步骤失败
- 写入结构化结果

目标 orchestrator：

- `image_task_orchestrator.py`
- `paper_task_orchestrator.py`
- `review_task_orchestrator.py`

### 6.4 能力层

建议目录：

```text
core/services/capabilities/
```

职责：

- 图像检测能力
- 文本检测能力
- LLM 解释能力
- 参考文献核验能力
- Review 相关性分析能力

目标 capabilities：

- `image_detection_service.py`
- `text_detection_service.py`
- `llm_analysis_service.py`
- `reference_check_service.py`
- `review_relevance_service.py`

### 6.5 集成层

建议目录：

```text
core/services/integrations/
```

职责：

- 统一封装外部 HTTP / SDK 调用
- 让业务层不再直接 `requests.post`

目标 integrations：

- `fastdetect_client.py`
- `openai_client.py`

### 6.6 事件日志入口

建议文件：

```text
core/services/event_logger.py
```

职责：

- 统一记录上传、建任务、开始检测、完成检测、失败、报告生成等事件
- 先统一入口，后面再扩成管理端完整日志模型
- 对应《架构共识.md》里“日志必须统一成事件模型”的共识

### 6.7 模型调用入口的长期约束

虽然本轮只计划先落地 `fastdetect_client.py` 和 `openai_client.py`，但代码组织必须直接体现《架构共识.md》中的模型治理要求：

- 模型调用入口必须统一放在 integrations / model client 层
- 业务层不直接依赖具体供应商 SDK 的协议细节
- 当前先做 OpenAI-compatible，不代表结构上只能支持 OpenAI-compatible
- 后续要能继续扩展到：
  - OpenAI 风格接口
  - Anthropic 风格接口
  - 完全自定义 HTTP API 接口

因此本轮即使不实现完整多协议，也必须避免把能力层写死为某一种接口格式。

---

## 7. 三类任务最终要交付什么

### 7.1 图像检测任务

用户闭环：

1. 上传图片或 ZIP/PDF
2. 提取图片
3. 选择待检测图片
4. 提交图像检测任务
5. 轮询状态
6. 查看结果和报告

后端闭环：

1. 资源层处理上传与抽图
2. 编排层创建任务
3. 能力层调用现有图像检测链路
4. 存储层写入 `DetectionResult` / `SubDetectionResult`
5. 状态接口返回统一结果

### 7.2 论文检测任务

用户闭环：

1. 上传论文文件
2. 创建论文检测任务
3. 轮询状态
4. 查看段落检测结果
5. 查看可疑段落解释
6. 查看参考文献结果
7. 查看论文内抽图后的图像检测结果

后端闭环：

1. 资源层提取正文、段落、图片、参考文献索引
2. 文本检测能力对段落逐段分析
3. 图像检测能力复用既有图像链路
4. LLM 能力解释可疑段落
5. 参考文献能力检查“是否存在”和“是否相关”
6. 结果写入论文专属结果表

### 7.3 同行评审检测任务

用户闭环：

1. 上传原论文文件
2. 上传对应 Review 文件
3. 创建评审检测任务
4. 轮询状态
5. 查看 Review 文本逐段检测结果
6. 查看 Review 段落与原文段落的相关性分析

后端闭环：

1. 资源层读取原论文和 review 两份输入
2. 文本检测能力处理 review 文本
3. LLM 能力做逐段相关性分析
4. 结果写入评审专属结果表

---

## 8. 每个 Slice 的具体执行方案

下面的 slice 不是抽象主题，而是可以逐阶段执行的施工单。

---

## 8.0 slice-00-tracking-bootstrap

### 目标

把根目录跟踪机制切换到本轮三路重构计划，确保后续所有推进都有统一记录口径。

### 必改文件

- `plan.md`
- `prd.json`
- `progress.md`

### 具体动作

- 用本计划覆写 `plan.md`
- 重置 `prd.json` 为本轮 slice 列表
- 清空旧进度，重写 `progress.md`
- 在计划和 AGENTS 约束里写入“验证成功后自动 commit 并尝试 push”

### 完成标准

- 跟踪文件能准确描述当前任务，而不是旧的图像排序修复任务

### 验证

- `Get-Content plan.md`
- `Get-Content progress.md`
- `Get-Content prd.json | ConvertFrom-Json`

---

## 8.1 slice-01-regression-baseline

### 目标

先把后端回归测试整理成三组，锁住当前三类任务入口行为，为后续重构提供护栏。

### 必改文件

- 新增 `core/tests/test_image_upload_flow.py`
- 新增 `core/tests/test_image_detection_flow.py`
- 新增 `core/tests/test_resource_task_flow.py`
- 必要时调整 `core/tests.py`
- 必要时调整 `core/tests/__init__.py`

### 具体动作

- 把旧 `core/tests.py` 里的图像检测回归用例迁入 `test_image_detection_flow.py`
- 把上传 API 的图像流程、论文上传、review 上传分别放进 `test_image_upload_flow.py`
- 新增资源任务创建用例：
  - `paper` 任务只接受 `paper`
  - `review` 任务必须同时具备 `review_paper` 和 `review_file`
  - `review_file` 必须正确关联 `linked_paper_file_id`
- 锁住当前论文结果接口的占位行为，避免后续改动时破坏契约

### 完成标准

- 三类任务入口行为都能被测试覆盖
- 后续重构失败时能立刻知道是上传、建任务还是结果读取坏了

### 验证

- `conda run -n detect python manage.py test core.tests`

---

## 8.2 slice-02-backend-skeleton

### 目标

先把服务层目录搭起来，让后续逻辑有固定落点，不再继续向 `views_*` 和 `tasks.py` 塞东西。

### 必改文件

- 新增 `core/services/__init__.py`
- 新增 `core/services/resources/__init__.py`
- 新增 `core/services/orchestrators/__init__.py`
- 新增 `core/services/capabilities/__init__.py`
- 新增 `core/services/integrations/__init__.py`
- 新增 `core/services/event_logger.py`
- 调整 `views_imageupload.py`
- 调整 `views_dectection.py`
- 调整 `views_review.py`

### 具体动作

- 建立目录结构和最小导出
- 在 `event_logger.py` 里先定义统一写事件的入口函数
- 把视图里的“纯业务逻辑”调用点替换成 service/orchestrator 调用
- 此阶段不要求实现完整业务迁移，但要把“迁移入口”搭好

### 完成标准

- 新业务不再需要直接落到 `views_*` 里
- 后端结构开始符合五层模型

### 验证

- `conda run -n detect python manage.py check`

---

## 8.3 slice-03-resource-layer

### 目标

把上传、抽图、文档预处理逻辑从视图里拆出来，形成统一资源入口。

### 必改文件

- 新增 `core/services/resources/file_ingestion_service.py`
- 新增 `core/services/resources/image_extraction_service.py`
- 新增 `core/services/resources/document_preprocessor.py`
- 调整 `views_imageupload.py`

### 具体动作

#### file_ingestion_service

负责：

- 统一处理上传参数
- 统一决定 `resource_type`
- 创建 `FileManagement`
- 保存原文件到 `stored_path`
- 处理 `linked_file`

#### image_extraction_service

负责：

- PDF 抽图
- ZIP 解包抽图
- 单图保存
- 创建 `ImageUpload`

#### document_preprocessor

负责输出统一结构，例如：

```json
{
  "text": "全文文本",
  "paragraphs": ["段落1", "段落2"],
  "images": [
    {
      "source": "page-1-image-1",
      "page_number": 1
    }
  ],
  "references": ["ref1", "ref2"]
}
```

支持输入：

- PDF
- DOCX
- TXT

### 完成标准

- 上传视图只保留请求适配
- 图像任务继续能抽图
- 论文和评审文件都能统一做文本/段落/引用预处理

### 验证

- 图片上传 API 测试通过
- 论文上传 API 测试通过
- Review 上传 API 测试通过

---

## 8.4 slice-04-image-detection-adapter

### 目标

把现有图像检测能力包成可复用 service，使它不再只属于图像页面。

### 必改文件

- 新增 `core/services/capabilities/image_detection_service.py`
- 新增 `core/services/orchestrators/image_task_orchestrator.py`
- 调整 `views_dectection.py`
- 复用 `local_detection.py`
- 复用 `call_figure_detection.py`

### 具体动作

#### image_detection_service

负责：

- 接收图片集合或 detection result 集合
- 调用现有本地图像检测链路
- 将结果回写到 `DetectionResult` / `SubDetectionResult`

#### image_task_orchestrator

负责：

- 创建/初始化图像检测任务
- 触发异步执行
- 管理失败回滚和状态推进

### 完成标准

- 图像检测原链路保持可用
- 论文检测之后可以直接复用图像能力，不需要再次改底层检测代码

### 验证

- 图像上传 -> 提交检测 -> 轮询状态 -> 查看结果 -> 报告下载 回归通过

---

## 8.5 slice-05-paper-closed-loop

### 目标

用真正的编排逻辑替换 `tasks.py` 里当前论文检测占位实现。

### 必改文件

- 新增 `core/services/orchestrators/paper_task_orchestrator.py`
- 新增 `core/services/capabilities/text_detection_service.py`
- 新增 `core/services/capabilities/reference_check_service.py`
- 新增 `core/services/capabilities/llm_analysis_service.py`
- 新增 `core/services/integrations/fastdetect_client.py`
- 新增 `core/services/integrations/openai_client.py`
- 调整 `tasks.py`
- 调整 `views_dectection.py`

### 具体动作

#### fastdetect_client

负责：

- 封装 FastDetectGPT API 调用
- 统一超时、错误处理、返回值解析

#### openai_client

负责：

- 封装 OpenAI-compatible 大模型调用
- 为未来多协议扩展留接口

#### text_detection_service

负责：

- 输入一组段落
- 调用 `fastdetect_client`
- 输出逐段概率和原始解释

#### llm_analysis_service

负责：

- 针对“疑似段落”生成解释说明
- 输出可直接给前端展示的说明文本

#### reference_check_service

负责：

- 对参考文献做最小闭环核验
- 至少返回：
  - 是否存在
  - 与正文是否相关

#### paper_task_orchestrator

按顺序做：

1. 读取论文资源文件
2. 走 `document_preprocessor`
3. 调 `text_detection_service`
4. 调 `image_detection_service` 分析抽图
5. 调 `llm_analysis_service`
6. 调 `reference_check_service`
7. 写入持久层结果
8. 更新任务状态

### 完成标准

- `/api/resource-task/create/` 的 `paper` 任务不再只是“把文本塞进 JSON 再标记 completed”
- 至少能返回：
  - 段落级检测结果
  - 可疑段落解释
  - 参考文献结果
  - 论文抽图后的图像检测结果

### 验证

- 创建 `paper` 任务后可轮询至完成
- `/api/paper-results/<id>/` 可读到结构化结果

---

## 8.6 slice-06-review-closed-loop

### 目标

让同行评审检测成为一条独立、可读、可测的任务流，而不是继续混在旧 review 逻辑里。

### 必改文件

- 新增 `core/services/orchestrators/review_task_orchestrator.py`
- 新增 `core/services/capabilities/review_relevance_service.py`
- 调整 `views_dectection.py`
- 调整 `views_review.py`

### 具体动作

#### review_relevance_service

负责：

- 把 review 段落与原论文段落做相关性分析
- 输出：
  - review paragraph
  - matched paper paragraph
  - relevance score / label
  - explanation

#### review_task_orchestrator

按顺序做：

1. 找到 `review_paper` 和 `review_file`
2. 预处理两份文档
3. 对 review 文本做逐段检测
4. 做 review 与原文段落的相关性分析
5. 写入评审结果表
6. 更新任务状态

### 完成标准

- 原论文 + review 文件能形成最小业务闭环
- 资源任务不再只停留在“文件上传成功”

### 验证

- Review 上传
- Review 任务创建
- 任务状态轮询
- 逐段相关性结果查询

---

## 8.7 slice-07-persistence-split

### 目标

把论文和评审文本结果从 `DetectionTask.text_detection_results` 里拆出来，建立专属结构化持久层。

### 必改文件

- 调整 `core/models.py`
- 新增 `core/migrations/0006_task_result_split.py`
- 新增 `core/migrations/0007_review_result_split.py`

### 新增模型

- `PaperDetectionResult`
- `PaperParagraphResult`
- `PaperReferenceResult`
- `ReviewDetectionResult`
- `ReviewParagraphResult`

### 设计要求

- `DetectionTask` 继续作为任务主表
- 图像结果仍由：
  - `ImageUpload`
  - `DetectionResult`
  - `SubDetectionResult`
  承载
- 论文和评审文本结果进入新表
- `text_detection_results` 过渡期保留兼容，但不能再作为主写入位置

### 完成标准

- 论文和评审结果有独立表结构
- 结果读取接口不再依赖 JSON 大字段

### 验证

- `conda run -n detect python manage.py migrate`
- `conda run -n detect python manage.py test core.tests`

---

## 8.8 slice-08-report-and-status-contract

### 目标

把三类任务的状态接口和报告接口规范化，避免前端继续读一堆条件分支。

### 必改文件

- 调整 `core/utils/report_generator.py`
- 调整 `core/views/views_dectection.py`
- 必要时新增 `core/utils/task_result_serializer.py`

### 具体动作

#### 状态接口规范化

`/api/detection-task/<id>/status/` 至少统一输出：

- `task_id`
- `task_name`
- `task_type`
- `status`
- `upload_time`
- `completion_time`
- `result_summary`
- `error_message`
- `is_running`
- `progress`
- `resource_files`
- `results`

其中 `results` 再按任务类型分结构：

- image：图片结果
- paper：论文段落/引用/抽图结果
- review：review 段落/相关性结果

#### 报告生成

`report_generator.py` 要从“仅图像中心”扩展到至少兼容 paper/review 报告骨架。

### 完成标准

- 前端读取任务详情时不再需要猜任务类型后的字段结构
- `/api/paper-results/<id>/` 不再直接从 JSON 字段读数据

### 验证

- 三类任务状态接口返回稳定结构
- 三类任务报告下载接口可用

---

## 8.9 slice-09-user-frontend-structure

### 目标

把用户端从“大页面 + 大 API 文件”改成按任务类型组织的结构，但不改外部路由。

### 保留页面入口

- `src/pages/upload.vue`
- `src/pages/history.vue`
- `src/pages/step/[id].vue`

这些页面保留为“装配页”，不再承担全部逻辑。

### 新增组件/模块

- `src/features/detection/components/DetectionTypeSwitcher.vue`
- `ImageTaskForm.vue`
- `PaperTaskForm.vue`
- `ReviewTaskForm.vue`
- `TaskProgressPanel.vue`
- `src/features/results/PaperResultView.vue`
- `ReviewResultView.vue`
- `src/api/detection.ts`
- `src/api/resourceTasks.ts`
- `src/api/reviewTasks.ts`

### 具体动作

- 从 `upload.vue` 中拆出任务类型切换、三类表单、进度展示
- 从 `publisher.ts` 拆出图像检测、资源任务、review 任务接口
- `history.vue` 和 `step/[id].vue` 改成按任务类型选择不同结果组件

### 完成标准

- 用户端结构与三类任务模型一致
- API 模块不再继续无限长大

### 验证

- `npm run type-check`
- `npm run build-only`
- 上传页三种任务手工冒烟

---

## 8.10 slice-10-admin-frontend-structure

### 目标

管理端不大改视觉结构，但数据视角要从“图像中心”转成“任务类型中心”。

### 保留页面入口

- `src/pages/files.vue`
- `src/pages/reviews.vue`
- `src/pages/logs.vue`
- `src/pages/analytics.vue`

### 新增组件/模块

- `src/features/tasks/TaskTypeFilter.vue`
- `TaskSummaryTable.vue`
- `src/features/logs/EventLogTable.vue`
- `src/features/analytics/TaskTypeCharts.vue`

### 具体动作

- 管理端任务列表支持按 `image/paper/review` 筛选
- 日志页开始按统一事件模型展示
- 统计页至少能看到三类任务的数量和趋势
- 拆分混杂 API 文件，按任务/日志/统计职责划分

### 完成标准

- 管理端能识别三类任务
- 日志与统计不再只偏向图像流程

### 验证

- `npm run type-check`
- `npm run build-only`
- 页面检查能看到 `image/paper/review`

---

## 8.11 slice-11-ai-service-minimal-guardrail

### 目标

尽量不碰 AI 服务主体，仅在绝对必要时新增很薄的论文/评审入口适配。

### 允许动作

- 新增单文件适配层，例如：
  - `AIDetector/code/ai-service/ai-service-code/paper_review_entry.py`

### 禁止动作

- 修改训练逻辑
- 修改 URN/LLM 方法实现
- 修改 pipeline 主体

### 完成标准

- 如果后端 service 层足以完成论文/评审闭环，则该 slice 标记 `no_change_needed`
- 如果必须动 AI 服务，也只能是薄适配

### 验证

- 无变更则在 `prd.json` 备注
- 有变更则做本地调用冒烟

---

## 8.12 slice-12-final-cleanup

### 目标

在所有主流程都跑通之后，清理已经被新结构取代的旧逻辑。

### 必改文件

- 调整 `core/tasks.py`
- 调整 `core/views/views_imageupload.py`
- 调整 `core/views/views_dectection.py`
- 调整 `core/views/views_review.py`
- 必要时调整 `core/models.py`

### 具体动作

- 删除 `tasks.py` 中旧论文直写逻辑
- 清理视图里遗留的业务分支
- 把 `DetectionTask.text_detection_results` 改为兼容只读，或在迁移完成后删除写入

### 完成标准

- 旧直连逻辑不再是主路径
- 新结构成为唯一主执行路径

### 验证

- 全量测试
- 前后端构建
- 三类任务端到端冒烟

---

## 9. 统一验证规则

### 9.1 每个 slice 完成后必须做什么

1. 更新 `prd.json`
2. 更新 `progress.md`
3. 执行对应验证
4. 验证成功后立刻 git commit
5. 立即尝试 git push
6. 如果 push 因网络或远端失败，记录失败信息，但不阻塞继续推进

### 9.2 后端最低验证要求

- `conda run -n detect python manage.py check`

涉及模型、迁移、任务流调整时追加：

- `conda run -n detect python manage.py migrate`
- `conda run -n detect python manage.py test core.tests`

### 9.3 前端最低验证要求

用户端：

- `npm run type-check`
- `npm run build-only`

管理端：

- `npm run type-check`
- `npm run build-only`

### 9.4 固定冒烟顺序

1. 图像任务上传与检测
2. 论文任务上传与结果查询
3. 评审任务上传与结果查询
4. 管理端任务列表
5. 管理端日志与统计

---

## 10. 跟踪规则

### 10.1 prd.json 结构

每个任务项必须包含：

- `id`
- `title`
- `status`
- `slice`
- `verification`
- `attempts`
- `fallback`

状态只允许：

- `pending`
- `in_progress`
- `done`
- `failed`

### 10.2 失败处理规则

同一子任务累计尝试 10 次仍无法稳定通过验证时：

- 标记为 `failed`
- 必须写明失败原因
- 必须写明 fallback
- 然后切换到更简单实现继续推进

例如 fallback：

- “保留旧接口 + 新增只读结果聚合层”
- “暂不拆除旧 JSON 字段，只切换主写入路径”

---

## 11. 本计划的交付标准

如果整个计划完成，最终应该达到下面这些标准。

### 11.1 用户视角

- 可以完成图像检测完整链路
- 可以完成论文检测完整链路
- 可以完成同行评审检测完整链路
- 检测历史能正确显示三类任务
- 任务详情页能按任务类型展示结果

### 11.2 后端视角

- `views_*` 变薄
- `core/services/` 成为主逻辑落点
- 图像能力可复用
- 文本能力可复用
- 论文和评审结果有专属表结构
- 外部模型/API 调用不再散落在业务层

### 11.3 管理端视角

- 能识别三类任务
- 能展示统一事件日志入口
- 能按任务类型做基础统计

### 11.4 工程视角

- 每个 slice 都有验证记录
- 每个成功 slice 都有对应 git commit
- push 成功最好，失败也必须有记录

---

## 12. 当前默认假设

- 默认策略是“接口稳定、内部重构”
- 不引入新 Django app
- 不改现有前后端路由路径
- 不碰 `ai-training`
- 论文和评审文本检测首期只支持 API 模式
- 本地模式仅预留能力层接口，不作为本轮交付要求
- 事件日志本轮只统一写入口，不强求完整日志中心 UI
- 管理端本轮只扩展到能看见三类任务，不做完整 IA 重构

---

## 13. 一句话总结

这次不是“随手修几个接口”，而是一次受控重构：

- 保持外部入口稳定
- 抽出统一资源层、编排层、能力层
- 让图像、论文、评审三条链路共享同一套后端骨架
- 先补测试，再搬代码
- 每个 slice 验证后立即 commit，并尝试 push

如果后续执行偏离以上原则，以本计划和 `架构共识.md` 为准，旧文档不作为目标依据。

## 14. paper-local-execution-hotfix

这是对 `slice-05-paper-closed-loop` 的紧急运行时修复补丁，不改后续 `slice-07` 及之后的设计边界。

目标：
- 消除 `/api/resource-task/create/` 在 `paper`/`review` 类型下对 Celery broker、`.delay()`、scheduler 注入分支的残留依赖
- 统一资源任务启动模型为“创建任务 -> 绑定资源 -> `transaction.on_commit(...)` -> `start_resource_detection_task_thread(...)`”
- 保持当前响应契约不变：`status = "in_progress"`、`execution_mode = "local_async"`

范围约束：
- 只修改资源任务启动链路、`core/tasks.py` 兼容入口、以及直接绑定的回归测试
- 不拆持久化结构，不新增迁移，不改前端结构，不重做报告协议
