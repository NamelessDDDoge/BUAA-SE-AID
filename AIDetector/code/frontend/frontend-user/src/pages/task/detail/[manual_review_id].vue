<template>
  <div class="task-detail pa-4">
    <!-- 返回按钮 -->
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="router.back()" class="mr-2 return-btn">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回我的任务</span>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content rounded-lg">
      <!-- 顶部信息区域 -->
      <div class="info-section pa-6">
        <div class="content-wrapper d-flex justify-center">
          <div class="content-container">
            <div class="info-content d-flex align-center justify-space-between pa-4">
              <!-- 左侧进度和标签 -->
              <div class="d-flex align-center" style="min-width: 320px; margin-left: 200px">
                <div class="progress-circle mr-3 elevation-1">
                  <span class="text-h5 font-weight-bold primary--text">{{
                    formatNumber(overall?.confidence_score) }}</span>
                  <span class="text-caption">为假</span>
                </div>
                <v-card class="ml-4 pa-2 elevation-1" flat rounded="lg" width="250">
                  <v-card-title class="pa-2 pb-1 text-subtitle-2 font-weight-bold">AI 检测结果</v-card-title>
                  <v-card-text class="pa-2 pt-1">
                    <!-- 造假维度列表 -->
                    <div v-for="(dimension, index) in detection_results" :key="index"
                      class="d-flex justify-space-between text-body-2 text-grey">
                      <span class="font-weight-medium">{{ convert(index) }}:</span>
                      <span class="text-primary">{{ dimension.probability.toFixed(2) }}</span> <!-- 占位符分数 -->
                    </div>
                  </v-card-text>
                </v-card>
              </div>

              <!-- 右侧任务信息 -->
              <div class="task-stats d-flex align-center">
                <div class="answer-card">

                  <v-row align="center" justify="start">
                    <v-col class="d-flex" cols="auto">
                      <div class="text-h6 font-weight-medium mb-4">审核进度</div>
                    </v-col>
                    <v-col class="d-flex align-center ml-4" cols="auto">
                      <v-btn color="primary" @click="handleSubmit">
                        提交
                      </v-btn>
                    </v-col>
                  </v-row>
                  <div class="answer-grid">
                    <v-btn v-for="(image, index) in images" :key="index" :color="getAnswerButtonColor(index)"
                      variant="outlined" size="small" class="answer-btn" density="compact"
                      @click="handleImageSelect(index)">
                      {{ index + 1 }}
                    </v-btn>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分割线 -->
      <v-divider></v-divider>

      <!-- 主要内容区域 -->
      <div class="content-wrapper d-flex pa-2 justify-center">
        <div class="content-container d-flex" style="gap: 12px;">
          <!-- 图片列表 -->
          <div class="image-list rounded-lg elevation-1"
            style="background-color: rgb(var(--v-theme-surface)); padding: 20px;">
            <div class="text-h6 font-weight-medium text-center mb-4" style="white-space: nowrap;">图片列表</div>
            <div class="image-grid">
              <div v-for="(image, index) in images" :key="index" class="image-grid-item"
                :class="{ 'active': currentImageIndex === index }" @click="handleImageSelect(index)">
                <v-img :src="getImageUrl(image.url)" cover width="100%" height="100%" class="rounded-lg"></v-img>
              </div>
            </div>
          </div>

          <!-- 图片预览区域 -->
          <div class="preview-section">
            <div class="preview-box">
              <v-img v-if="currentImage" :src="getImageUrl(currentImage.url)" contain height="100%"
                class="rounded-lg"></v-img>
              <!-- 为每个维度创建独立的画布 -->
              <template v-for="(dimension, index) in dimensionsPerImage[currentImageIndex]" :key="index">
                <canvas v-show="currentDrawingDimension === index"
                  :ref="el => { if (el) drawingCanvases[index] = el as HTMLCanvasElement }" class="drawing-canvas"
                  :class="{ 'active': currentDrawingDimension === index }"
                  style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"></canvas>
              </template>
              <transition name="fade">
                <v-img v-if="activeOverlay && isOverlayVisible" :src="activeOverlay"
                  class="rounded-lg overlay-image"></v-img>
              </transition>
              <div class="preview-controls">
                <v-btn icon="mdi-chevron-left" variant="flat" @click="handlePrevImage"
                  :disabled="currentImageIndex <= 0" class="control-btn" color="black" size="x-large"></v-btn>
                <v-btn icon="mdi-chevron-right" variant="flat" @click="handleNextImage"
                  :disabled="currentImageIndex >= images.length - 1" class="control-btn" color="black"
                  size="x-large"></v-btn>
              </div>
            </div>
          </div>

          <!-- 评分维度区域 -->
          <div class="dimension-section rounded-lg elevation-1">
            <div class="text-h6 font-weight-medium mb-4">评分维度</div>
            <div class="text-caption text-medium-emphasis mb-4">
              请根据图片特征，对每个造假方式进行可能性评估，分值越大表示相应维度造假可能性越大，必要时可使用绘制标注功能标记具体位置。</div>
            <div class="dimension-list">
              <div v-for="(dimension, index) in dimensionsPerImage[currentImageIndex]" :key="index"
                class="dimension-item mb-6">
                <div class="d-flex align-center justify-space-between mb-2">
                  <span class="text-subtitle-1">{{ dimension.name }}</span>
                  <div class="d-flex">
                    <v-btn size="small" color="primary" variant="tonal" @click="openDrawingDialog(index)" class="mr-2">
                      <v-icon size="small" icon="mdi-pencil" class="mr-1"></v-icon>
                      绘制标注
                    </v-btn>
                    <v-btn size="small" :color="urn[index]?.visible ? 'error' : 'grey'" variant="tonal"
                      @click="handleDisplayFake(urn[index])" class="fake-area-btn">
                      <v-icon size="small" :icon="urn[index]?.visible ? 'mdi-eye-off' : 'mdi-eye'"
                        class="mr-1"></v-icon>
                      {{ urn[index]?.visible ? '隐藏造假区域' : '显示造假区域' }}
                    </v-btn>
                  </div>
                </div>
                <div class="degree-buttons mb-2">
                  <v-btn-group variant="outlined" class="d-flex">
                    <v-btn v-for="option in degreeOptions" :key="option.value"
                      :color="dimension.value === option.value ? getDegreeColor(option.value) : 'grey'"
                      :variant="dimension.value === option.value ? 'flat' : 'outlined'" class="flex-grow-1"
                      @click="dimension.value = option.value" size="small">
                      {{ option.value }}
                    </v-btn>
                  </v-btn-group>
                </div>
                <v-text-field v-model="dimension.reason" :label="'请输入' + dimension.name + '的理由'" variant="outlined"
                  density="compact" hide-details class="mt-2"></v-text-field>
              </div>

              <!-- 造假判定按钮组 -->
              <div class="fake-judge-section mt-4 pt-4">
                <div class="text-subtitle-1 mb-4">造假判定</div>
                <div class="d-flex justify-space-between">
                  <v-btn :color="imageJudgements[currentImageIndex] === true ? 'error' : 'grey-lighten-1'"
                    variant="tonal" class="flex-grow-1 mr-2" @click="handleJudgement(true)">
                    造假图片
                  </v-btn>
                  <v-btn :color="imageJudgements[currentImageIndex] === false ? 'success' : 'grey-lighten-1'"
                    variant="tonal" class="flex-grow-1" @click="handleJudgement(false)">
                    真实图片
                  </v-btn>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加提示对话框 -->
    <v-dialog v-model="showAlert" max-width="400">
      <v-card>
        <v-card-text class="pa-4">
          <div class="text-center">{{ alertMessage }}</div>
        </v-card-text>
        <v-card-actions class="justify-center pb-4">
          <v-btn color="primary" variant="text" @click="showAlert = false">
            确定
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 绘制弹窗 -->
    <DrawingDialog v-model="showDrawingDialog" :image-url="currentImage ? getImageUrl(currentImage.url) : ''"
      :initial-paths="currentDimensionPaths" @save="handleDrawingSave" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import reviewer from '@/api/reviewer'
import type { RouteParams } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import DrawingDialog from '@/components/DrawingDialog.vue'
import publisher from '@/api/publisher'

const router = useRouter()
const snackbar = useSnackbarStore()
const route = useRoute()

interface Image {
  id: number,
  url: string
}

interface SubMethod {
  method: string
  probability: number
  mask_image: string
  mask_matrix: any | null
  visible: boolean
}

// 图片相关数据和方法
const currentImageIndex = ref(0)
const images = ref<Image[]>([])

const manual_review_id = computed(() => (route.params as RouteParams & { manual_review_id: number }).manual_review_id)
const imageJudgements = ref<(boolean | null)[]>([])
const dimensionsPerImage = ref<Dimension[][]>([])
const urn = ref<SubMethod[]>([])
const activeOverlay = ref()
const isOverlayVisible = ref(false)
const overall = ref()
const detection_results = ref<dimension[]>([])

interface dimension {
  method: string,
  probability: number
}

const convert = (index: number) => {
  switch (index) {
    case 0:
      return '高斯模糊'
    case 1:
      return '亮度/对比度调节'
    case 2:
      return '智能修复'
    case 3:
      return '暴力覆盖'
    case 4:
      return '同图复制'
    case 5:
      return '重叠切割'
    case 6:
      return '跨图拼接'
  }
}


const fetchDetectionResults = async () => {
  try {
    const id = await (await publisher.getDetectionID({ img_id: currentImage.value?.id })).data.
      detection_result_id
    const response = (await publisher.getSingleImageResult(id)).data
    detection_results.value = response.sub_methods
  } catch (error) {
    snackbar.showMessage('获取检测结果失败', 'error')
  }
}


const formatNumber = (result: number) => {
  return `${(result * 100).toFixed(2)}%`
}


onMounted(async () => {
  try {
    const response = (await reviewer.getReviewTaskDetail({ manual_review_id: manual_review_id.value })).data
    images.value = response.imgs
    imageJudgements.value = new Array(images.value.length).fill(null)

    // 为每个图片的每个维度初始化独立的数据
    dimensionsPerImage.value = images.value.map(() => [
      { name: '高斯模糊', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '亮度/对比度调节', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '智能修复', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '暴力覆盖', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '同图复制', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '重叠切割', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
      { name: '跨图拼接', value: null, reason: '', showFakeArea: false, drawingPaths: [] }
    ])
    fetchMaskImage()
    fetchDetectionResults()

  } catch (error) {
    snackbar.showMessage('获取任务详情失败', 'error')
  }
})

const currentImage = computed(() => {
  if (
    Array.isArray(images.value) &&
    typeof currentImageIndex.value === 'number' &&
    currentImageIndex.value >= 0 &&
    currentImageIndex.value < images.value.length
  ) {
    return images.value[currentImageIndex.value];
  }
  return null;
});

const getImageUrl = (url: string) => {
  return import.meta.env.VITE_API_URL + url
}

const fetchMaskImage = async () => {
  try {
    const res = (await reviewer.getMaskImage({ img_id: currentImage.value?.id })).data
    urn.value = res.sub_methods.map((item: Omit<SubMethod, 'visible'>) => ({
      ...item,
      visible: false
    }))
    overall.value = res.overall
  } catch (error) {
    snackbar.showMessage('获取mask失败', 'error')
  }
}

const handleDisplayFake = (dimension: SubMethod) => {
  if (dimension.visible) {
    dimension.visible = false
    isOverlayVisible.value = false
    activeOverlay.value = null
    return
  }

  // 关闭其他所有覆盖层
  urn.value.forEach(d => {
    if (d !== dimension) {
      d.visible = false
    }
  })

  // 显示当前覆盖层
  dimension.visible = true
  isOverlayVisible.value = true
  activeOverlay.value = dimension.mask_image
}

const handleImageSelect = (index: number) => {
  currentImageIndex.value = index
  currentDrawingDimension.value = -1 // 重置绘制状态
  fetchMaskImage()
  fetchDetectionResults()
}

const handlePrevImage = () => {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

const handleNextImage = () => {
  if (currentImageIndex.value < images.value.length - 1) {
    currentImageIndex.value++
  }
}

// 评分维度数据
interface Dimension {
  name: string;
  value: number | null;
  reason: string;
  showFakeArea: boolean;
  drawingPaths: Array<{
    points: Array<{ x: number, y: number }>;
    color: string;
  }>;
}

const drawingCanvases = ref<HTMLCanvasElement[]>([])
const imageRect = ref<DOMRect | null>(null)
const currentDrawingDimension = ref<number>(-1)

// 计算当前维度的笔迹列表
const currentDimensionPaths = computed(() => {
  if (currentDrawingDimension.value === -1) return []
  const currentImage = dimensionsPerImage.value[currentImageIndex.value]
  if (!currentImage) return []
  const currentDim = currentImage[currentDrawingDimension.value]
  return currentDim?.drawingPaths || []
})

// 打开绘制对话框
const openDrawingDialog = (index: number) => {
  currentDrawingDimension.value = index
  showDrawingDialog.value = true
}

// 处理绘制保存
const handleDrawingSave = (paths: Array<{ points: Array<{ x: number; y: number }>; color: string }>) => {
  if (currentDrawingDimension.value === -1) return

  const currentImage = dimensionsPerImage.value[currentImageIndex.value]
  if (!currentImage) return

  // 只更新当前维度的绘制路径
  currentImage[currentDrawingDimension.value].drawingPaths = [...paths]
}

// 监听图片加载完成
watch(() => currentImage.value?.url, () => {
  const imgElement = document.querySelector('.preview-box .v-img img') as HTMLImageElement
  if (imgElement) {
    if (imgElement.complete) {
      imageRect.value = imgElement.getBoundingClientRect()
    } else {
      imgElement.onload = () => {
        imageRect.value = imgElement.getBoundingClientRect()
      }
    }
  }
})

// 监听窗口大小变化
onMounted(() => {
  window.addEventListener('resize', () => {
    const imgElement = document.querySelector('.preview-box .v-img img') as HTMLImageElement
    if (imgElement) {
      imageRect.value = imgElement.getBoundingClientRect()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', () => { })
})

const degreeOptions = [
  { value: 1, label: '轻微' },
  { value: 2, label: '一般' },
  { value: 3, label: '中等' },
  { value: 4, label: '明显' },
  { value: 5, label: '严重' }
]

const getDegreeColor = (value: number) => {
  switch (value) {
    case 1:
      return 'success'
    case 2:
      return 'info'
    case 3:
      return 'yellow'
    case 4:
      return 'warning'
    case 5:
      return 'error'
    default:
      return 'grey'
  }
}

// 处理造假判定
const handleJudgement = (isFake: boolean) => {
  imageJudgements.value[currentImageIndex.value] = isFake
}

// 获取答题卡按钮颜色
const getAnswerButtonColor = (index: number) => {
  if (index === currentImageIndex.value) return 'primary'
  const judgement = imageJudgements.value[index]
  if (judgement === null) return 'grey'
  return judgement ? 'error' : 'success'
}

const showAlert = ref(false)
const alertMessage = ref('')

const checkAnswerCompletion = () => {
  // 检查每张图片是否都已完成评分和判定
  for (let i = 0; i < images.value.length; i++) {
    // 检查造假判定是否已完成
    if (imageJudgements.value[i] === null) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片尚未进行造假判定`
      }
    }
  }

  for (let i = 0; i < dimensionsPerImage.value.length; i++) {
    const dims = dimensionsPerImage.value[i]

    const hasUnratedDimension = dims.some(dim => dim.value === null)
    if (hasUnratedDimension) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片的评分维度尚未评分完整`
      }
    }

    const hasEmptyReason = dims.some(dim => !dim.reason)
    if (hasEmptyReason) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片的评分维度理由尚未填写完整`
      }
    }
  }

  return {
    complete: true,
    message: '所有图片已完成评分'
  }
}

interface ImageItem {
  img_id: number
  score: Array<number | null>  // 维度得分数组，可能是数值或者null
  reason: Array<string | null>  // 维度理由数组，可能是字符串或者null
  final: boolean | null  // 造假判定结果
  points: Array<Array<{}>>
}

const constructData = () => {
  const data = { result: [] as ImageItem[] }
  for (let i = 0; i < images.value.length; i++) {
    const item: ImageItem = {
      img_id: images.value[i].id,
      score: dimensionsPerImage.value[i].map(dim => dim.value),
      reason: dimensionsPerImage.value[i].map(dim => dim.reason),
      final: imageJudgements.value[i],
      points: dimensionsPerImage.value[i].map(dim => dim.drawingPaths)
    }
    data.result.push(item)
  }
  console.log(data)
  return data
}

const handleSubmit = async () => {
  const result = checkAnswerCompletion()
  if (!result.complete) {
    // 显示错误提示
    snackbar.showMessage(result.message, 'error')
    return
  } else {
    try {
      await reviewer.submitReview(manual_review_id.value, constructData())
      snackbar.showMessage("提交成功", 'success')
    } catch (error) {
      snackbar.showMessage('提交失败', 'error')
    }
  }
}

const showDrawingDialog = ref(false)

// 监听图片切换
watch(() => currentImageIndex.value, () => {
  currentDrawingDimension.value = -1 // 重置绘制状态
})

// 监听维度切换
watch(() => currentDrawingDimension.value, (newVal, oldVal) => {
  // 确保所有画布都被隐藏
  drawingCanvases.value.forEach((canvas, index) => {
    if (canvas) {
      canvas.style.display = 'none'
    }
  })

  // 只显示当前维度的画布
  if (newVal !== -1) {
    const newCanvas = drawingCanvases.value[newVal]
    if (newCanvas) {
      newCanvas.style.display = 'block'
    }
  }
})
</script>

<style scoped>
.task-detail {
  position: relative;
  min-height: 100vh;
  max-height: 100vh;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.main-content {
  height: calc(100vh - 80px);
  overflow: hidden;
  background-color: rgb(var(--v-theme-surface));
}

.info-section {
  background-color: rgb(var(--v-theme-surface));
  padding: 16px 0;
}

.info-content {
  width: 100%;
  background-color: rgb(var(--v-theme-surface));
  min-height: 160px;
  padding: 12px 16px !important;
  justify-content: center;
  gap: 24px;
}

.progress-circle {
  width: clamp(100px, 8vw, 130px);
  height: clamp(100px, 8vw, 130px);
  border-radius: 50%;
  border: 5px solid rgb(var(--v-theme-primary));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-surface));
}

.progress-circle .text-h5 {
  font-size: clamp(1.8rem, 2vw, 2.5rem) !important;
  line-height: 1.2;
}

.progress-circle .text-caption {
  font-size: 1rem !important;
  margin-top: 4px;
}

.task-list {
  width: clamp(360px, 30vw, 420px);
  padding: 0 12px;
}

.task-item {
  width: 100%;
  margin-bottom: 12px;
}

.task-item .v-progress-linear {
  width: clamp(260px, 25vw, 340px) !important;
  height: 10px !important;
}

.task-item .text-h6 {
  white-space: nowrap;
}

.content-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.content-container {
  width: 100%;
  max-width: min(1200px, 95vw);
  display: flex;
  justify-content: center;
}

.task-stats {
  min-width: 320px;
  justify-content: center;
}

.answer-card {
  padding: 16px;
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-width: 280px;
  margin-right: 200px
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.overlay-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  mix-blend-mode: multiply;
  opacity: 0.7;
  object-fit: contain;
}


.answer-btn {
  width: 36px !important;
  min-width: 0 !important;
  height: 36px !important;
  padding: 0 !important;
}

@media (max-width: 1280px) {
  .task-stats {
    min-width: clamp(280px, 25vw, 320px);
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.image-list {
  width: clamp(100px, 8vw, 120px);
  height: calc(100vh - 380px);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.image-grid {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  margin-top: -8px;
}

.image-grid-item {
  width: 80px;
  height: 80px;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.2s ease;
  border: 2px solid transparent;
  flex-shrink: 0;
}

.image-grid-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.image-grid-item.active {
  border-color: rgb(var(--v-theme-primary));
}

.preview-section {
  flex: 1;
  min-width: 0;
  max-width: min(800px, 60vw);
  margin: 0 12px;
}

.preview-box {
  position: relative;
  height: calc(100vh - 380px);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  overflow: hidden;
}

.preview-box .v-img {
  max-width: 800px;
  max-height: 100%;
  object-fit: contain;
}

.preview-controls {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
}

.control-btn {
  opacity: 0.7;
  transition: opacity 0.2s ease !important;
}

.control-btn:hover {
  opacity: 1;
  transform: none;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-primary), 0.4);
}

@media (max-width: 960px) {
  .content-container {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .preview-section {
    max-width: 100%;
    order: -1;
  }

  .image-list {
    height: auto;
    min-height: 300px;
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.dimension-section {
  width: 360px;
  padding: 20px;
  background-color: rgb(var(--v-theme-surface));
  height: calc(100vh - 380px);
  overflow-y: auto;
}

.dimension-list {
  padding-right: 12px;
}

.dimension-item {
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.1);
  padding-bottom: 16px;
}

.dimension-item:last-child {
  border-bottom: none;
}

@media (max-width: 1280px) {
  .dimension-section {
    width: 260px;
  }
}

.fake-judge-section {
  border-top: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.degree-buttons {
  width: 100%;
}

.degree-buttons .v-btn {
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.875rem;
}

.fake-area-btn {
  font-size: 0.75rem;
  text-transform: none;
  letter-spacing: 0;
  min-width: 120px;
  /* 确保按钮有固定的最小宽度 */
}

.drawing-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  display: none;
}

.drawing-canvas.active {
  pointer-events: auto;
  cursor: crosshair;
  display: block;
}

.color-preview {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>