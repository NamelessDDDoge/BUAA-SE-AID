<template>
  <div class="task-detail pa-4">
    <!-- 返回按钮 -->
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="router.back()" class="mr-2 return-btn">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回检测历史</span>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-content rounded-lg">
      <!-- 顶部信息区域 -->
      <div class="info-section pa-6">
        <div class="content-wrapper d-flex justify-center">
          <div class="content-container">
            <div class="info-content d-flex align-center justify-space-between pa-4">
              <!-- 左侧进度和标签 -->
              <div class="d-flex align-center" style="min-width: 320px">
                <div class="progress-circle mr-3 elevation-1">
                  <!-- <span class="text-h5 font-weight-bold primary--text">{{ taskData?.progress }}%</span> -->
                  <span class="text-h5 font-weight-bold primary--text">{{ formatNumber(AI_detection) }}</span>
                  <span class="text-caption">为假</span>
                </div>
                <v-btn color="primary" variant="elevated" prepend-icon="mdi-download" @click="handleDownloadReport"
                  class="ml-4">
                  下载人工审核报告
                </v-btn>
                <!-- 添加的v-card文本区域 -->
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
                <div class="stat-item mr-4">
                  <div class="text-subtitle-1 d-flex justify-center">
                    <v-chip variant="flat" size="x-large" class="unprocessed-chip font-weight-medium px-3"
                      style="min-width: 80px">
                      未处理
                    </v-chip>
                  </div>
                  <div class="text-h6 font-weight-bold">{{ process }}份</div>
                </div>
                <div class="stat-item">
                  <div class="text-subtitle-1 d-flex justify-center">
                    <v-chip variant="flat" size="x-large" class="sent-chip font-weight-medium px-3"
                      style="min-width: 80px">
                      已发送
                    </v-chip>
                  </div>
                  <div class="text-h6 font-weight-bold">{{ done }}份</div>
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
                <v-img :src="getImageUrl(image.img_url)" cover width="100%" height="100%" class="rounded-lg"></v-img>
              </div>
            </div>
          </div>

          <!-- 图片预览区域 -->
          <div class="preview-section">
            <div class="preview-box">
              <v-img v-if="currentImage" :src="getImageUrl(currentImage.img_url)" contain height="100%"
                class="rounded-lg"></v-img>
              <span v-else class="text-h4">PIC</span>
              <div class="preview-controls">
                <v-btn icon="mdi-chevron-left" variant="flat" @click="handlePrevImage"
                  :disabled="currentImageIndex <= 0" class="control-btn" color="black" size="x-large"></v-btn>
                <v-btn icon="mdi-chevron-right" variant="flat" @click="handleNextImage"
                  :disabled="currentImageIndex >= images.length - 1" class="control-btn" color="black"
                  size="x-large"></v-btn>
              </div>
            </div>
          </div>

          <!-- 右侧人工审核区域 -->
          <div class="review-section rounded-lg elevation-1 pa-4">
            <div class="review-header">
              <div class="text-h6 font-weight-medium text-center mb-4">人工审核</div>
              <div class="reviewer-info mt-4">
                <template v-if="review_results.length > 0">
                  <div v-for="(review, index) in review_results" :key="index"
                    class="reviewer-item d-flex align-center pa-3 mb-4 rounded" style="min-height: 64px;">
                    <v-avatar size="40" class="mr-3" color="primary">
                      <v-img v-if="review.avatar" :src="getImageUrl(review.avatar)" cover></v-img>
                      <span v-else class="text-h6">{{ review.username.charAt(0) }}</span>
                    </v-avatar>
                    <div class="flex-grow-1">
                      <div class="text-body-1 font-weight-medium">{{ review.username }}</div>
                      <div class="text-caption text-grey mt-1">结果：{{ getResult(review.result) }}</div>
                    </div>
                    <v-btn variant="text" density="comfortable" class="details-btn" color="primary"
                      @click="handleViewDetail(review)">
                      查看详情
                      <v-icon size="16" class="ml-1">mdi-chevron-right</v-icon>
                    </v-btn>
                  </div>
                </template>
                <template v-else>
                  <div class="d-flex flex-column align-center justify-center" style="height: 200px;">
                    <v-icon size="48" color="grey" class="mb-4">mdi-information-outline</v-icon>
                    <div class="text-body-1 text-grey">暂无人工审核结果</div>
                  </div>
                </template>
              </div>
            </div>
          </div>


        </div>
      </div>
    </div>

    <!-- 添加详情弹窗 -->
    <v-dialog v-model="showDetailDialog" fullscreen :scrim="false" transition="dialog-bottom-transition">
      <v-card>
        <v-toolbar dark color="primary">
          <v-btn icon dark @click="showDetailDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-toolbar-title>检测详情</v-toolbar-title>
          <v-spacer></v-spacer>
        </v-toolbar>
        <result-component v-if="showDetailDialog" :task-id="taskData?.id"
          :imageUrl="getImageUrl(images[currentImageIndex].img_url)" :reasons="reasons" :result="result"
          :scores="scores" :ai_detection="AI_detection" :annotations="annotations" />
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useUserStore } from '@/stores/user'
import { useSnackbarStore } from '@/stores/snackbar'
import ResultComponent from '@/components/result.vue'
import publisher from '@/api/publisher'

const router = useRouter()
const route = useRoute()
const theme = useTheme()
const userStore = useUserStore()
const snackbar = useSnackbarStore()

const review_request_id = computed(() => (route.params as RouteParams & { review_request_id: number }).review_request_id)

interface Task {
  id: string
  publishTime: string
  reviewer: string
  progress: number
  publisherId: string
}

interface Image {
  img_id: string
  img_url: string
  thumbnail: string
  reviewStatus: string
  reviewComment?: string
}

interface Review {
  id: number,
  username: string,
  avatar: string,
  result: boolean
}

// 定义路由参数的类型
interface RouteParams {
  id: string
}

interface dimension {
  method: string,
  probability: number
}


const taskData = ref<Task | null>(null)
const images = ref<Image[]>([])
const currentImageIndex = ref(0)
const done = ref(0)
const process = ref(0)
const AI_detection = ref(0)
const review_results = ref<Review[]>([])
const reasons = ref<string[]>([])
const result = ref(false)
const scores = ref<number[]>([])
const annotations = ref<Array<Array<{ points: { x: number; y: number; }[]; color: string; }>>>([])
const detection_results = ref<dimension[]>([])


const currentImage = computed(() => {
  return images.value[currentImageIndex.value]
})

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


// 获取检测结果
const fetchDetectionResults = async () => {
  try {
    const id = await (await publisher.getDetectionID({ img_id: currentImage.value.img_id })).data.
      detection_result_id
    const response = (await publisher.getSingleImageResult(id)).data
    detection_results.value = response.sub_methods
  } catch (error) {
    snackbar.showMessage('获取检测结果失败', 'error')
  }
}

const fetchReview = async (img: Image) => {
  try {
    review_results.value = (await publisher.getImageReviewAll({ review_request_id: review_request_id.value, img_id: img.img_id })).data.reviewers_results
  } catch (error) {
    snackbar.showMessage('获取人工审核结果失败', 'error')
  }
}

const fetchReviewDetail = async (review: Review) => {
  try {
    const response = (await publisher.getImageReviewDetail({ review_request_id: review_request_id.value, img_id: currentImage.value.img_id, reviewer_id: review.id })).data
    reasons.value = response.reasons
    result.value = response.result
    scores.value = response.scores
    annotations.value = response.points
    console.log(annotations.value)
  } catch (error) {
    snackbar.showMessage('获取人工审核详情失败', 'error')
  }
}

const handleImageSelect = (index: number) => {
  currentImageIndex.value = index
  fetchReview(currentImage.value)
  fetchDetectionResults()
}

const getResult = (result: boolean) => {
  if (result === true) {
    return '假'
  } else {
    return '真'
  }
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

const getImageUrl = (url: string) => {
  return import.meta.env.VITE_API_URL + url
}


// 添加弹窗控制变量
const showDetailDialog = ref(false)

const formatNumber = (result: number) => {
  return `${(result * 100).toFixed(2)}%`
}

// 修改查看详情按钮的点击事件
const handleViewDetail = (review: Review) => {
  showDetailDialog.value = true
  fetchReviewDetail(review)
}

const handleDownloadReport = async () => {
  try {
    const response = await publisher.downloadReviewReport({ review_request_id: review_request_id.value })
    // 打印response.data（Blob对象）的类型和大小
    console.log('Downloaded data is a Blob. Type:', response.data.type, 'Size:', response.data.size);

    // 确保response.data是一个Blob对象
    if (!(response.data instanceof Blob)) {
      console.error('Expected Blob data, but received:', response.data);
      snackbar.showMessage('下载失败：未收到文件数据', 'error');
      return;
    }

    const blob = response.data

    // 检查Blob类型是否为PDF
    if (blob.type !== 'application/pdf') {
      console.warn('Downloaded Blob type is not application/pdf:', blob.type);
      snackbar.showMessage('下载的文件不是PDF格式', 'warning');
      return;
    }

    // 创建一个 Blob URL
    const url = window.URL.createObjectURL(blob)
    // 创建一个下载链接
    const link = document.createElement('a')
    link.href = url
    link.download = `人工审核报告_${review_request_id.value}.pdf`
    link.target = '_blank' // 在新标签页打开
    document.body.appendChild(link)
    link.click()
    // 清理
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    snackbar.showMessage('报告下载成功', 'success')
  } catch (error) {
    snackbar.showMessage('报告下载失败', 'error')
  }
}

onMounted(async () => {
  // 先检查权限
  //const hasPermission = await checkTaskPermission()
  const hasPermission = true
  if (!hasPermission) return
  try {
    const response = (await publisher.getRequestDetail({ review_request_id: review_request_id.value })).data
    done.value = response.status.done
    process.value = response.status.process
    AI_detection.value = response.ai_detection_result.confidence_score
    images.value = response.images
    review_results.value = (await publisher.getImageReviewAll({ review_request_id: review_request_id.value, img_id: images.value[0].img_id })).data.reviewers_results
    currentImageIndex.value = 0
    fetchDetectionResults()
  } catch (error) {
    snackbar.showMessage('获取人工审核结果失败', 'error')
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

.review-section {
  width: clamp(260px, 20vw, 300px);
  padding: 20px;
  background-color: rgb(var(--v-theme-surface));
  height: calc(100vh - 380px);
  overflow-y: auto;
  flex-shrink: 0;
  position: relative;
}

.review-header {
  position: sticky;
  top: 0;
  background-color: rgb(var(--v-theme-surface));
  z-index: 1;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.reviewer-item {
  position: relative;
  padding: 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
  background-color: rgba(var(--v-theme-surface), 0.5);
  border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.reviewer-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.05);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.details-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
  white-space: nowrap;
}

.reviewer-item:hover .details-btn {
  opacity: 1;
}

.unprocessed-chip {
  background-color: rgba(244, 67, 54, 0.1) !important;
  color: rgb(244, 67, 54) !important;
}

.sent-chip {
  background-color: rgba(76, 175, 80, 0.1) !important;
  color: rgb(76, 175, 80) !important;
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

.task-stats {
  min-width: 320px;
  justify-content: center;
}

.stat-item {
  min-width: 120px;
}

.stat-item .text-h6 {
  font-size: 1.8rem !important;
  text-align: center;
  margin-top: 8px;
}

@media (max-width: 1280px) {
  .task-stats {
    min-width: clamp(280px, 25vw, 320px);
  }

  .stat-item {
    min-width: clamp(100px, 10vw, 120px);
  }

  .stat-item .text-h6 {
    font-size: clamp(1.4rem, 1.5vw, 1.8rem) !important;
  }
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

  .image-list,
  .review-section {
    height: auto;
    min-height: 300px;
  }
}

/* 添加弹窗过渡动画样式 */
.dialog-bottom-transition-enter-active,
.dialog-bottom-transition-leave-active {
  transition: transform 0.2s ease-in-out;
}

.dialog-bottom-transition-enter-from,
.dialog-bottom-transition-leave-to {
  transform: translateY(100%);
}
</style>