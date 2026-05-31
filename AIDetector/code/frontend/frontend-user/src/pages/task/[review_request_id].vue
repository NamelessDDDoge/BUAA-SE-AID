<template>
  <div class="publisher-progress-page">
    <div class="page-shell">
      <div class="hero-bar">
        <div>
          <div class="eyebrow">Publisher Review Progress</div>
          <h1>人工审核进度</h1>
          <p>查看已发送人数、已完成结果、原始文件和每位审核员的处理情况。</p>
        </div>
        <div class="hero-actions">
          <v-btn variant="tonal" prepend-icon="mdi-arrow-left" @click="goBack">返回</v-btn>
          <v-btn color="primary" prepend-icon="mdi-download" @click="handleDownloadReport">下载人工审核报告</v-btn>
        </div>
      </div>

      <v-row class="overview-grid" dense>
        <v-col cols="12" md="4">
          <v-card class="glass-card progress-card" rounded="xl" elevation="0">
            <div class="progress-ring">
              <div>
                <div class="progress-value">{{ primaryMetricValue }}</div>
                <div class="progress-label">{{ primaryMetricLabel }}</div>
              </div>
            </div>
            <div class="progress-meta">
              <v-chip color="primary" variant="tonal">{{ statusText }}</v-chip>
              <v-chip color="teal" variant="tonal">{{ done }} 已完成</v-chip>
              <v-chip color="amber" variant="tonal">{{ process }} 待完成</v-chip>
            </div>
            <v-progress-linear :model-value="progressPercent" height="12" rounded color="primary" class="mt-4" />
            <div class="text-caption text-medium-emphasis mt-2">完成率 {{ progressPercent.toFixed(0) }}%</div>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card class="glass-card summary-card" rounded="xl" elevation="0">
            <div class="card-title">任务摘要</div>
            <div class="summary-list">
              <div class="summary-row"><span>请求编号</span><strong>{{ reviewRequestId }}</strong></div>
              <div class="summary-row"><span>{{ taskFocusLabel }}</span><strong>{{ taskFocusValue }}</strong></div>
              <div class="summary-row"><span>审核员</span><strong>{{ reviewers.length }}</strong></div>
              <div class="summary-row"><span>文件数</span><strong>{{ originalFiles.length || images.length || 0 }}</strong></div>
            </div>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card class="glass-card summary-card" rounded="xl" elevation="0">
            <div class="card-title">检测概览</div>
            <div v-for="item in overviewRows" :key="item.label" class="dimension-mini">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
            <div v-if="!overviewRows.length" class="empty-state compact">暂无检测概览</div>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="workspace-grid" dense>
        <v-col cols="12" lg="3">
          <v-card class="glass-card side-panel" rounded="xl" elevation="0">
            <div class="card-title">原始文件</div>
            <div class="file-list">
              <div v-for="file in originalFiles" :key="file.id || file.file_id" class="file-item">
                <div class="file-main">
                  <div class="file-name">{{ file.file_name }}</div>
                  <div class="file-meta">{{ file.resource_type }} · {{ file.file_type }}</div>
                </div>
                <div class="file-actions">
                  <v-btn size="small" variant="text" prepend-icon="mdi-eye-outline" @click="previewFile(file)">预览</v-btn>
                  <v-btn size="small" variant="text" prepend-icon="mdi-download" :disabled="!file.file_url" @click="downloadFile(file)">下载</v-btn>
                  <v-btn
                    v-if="requestType === 'resource'"
                    size="small"
                    variant="text"
                    prepend-icon="mdi-file-document-outline"
                    @click="openExtractDialog(file)"
                  >
                    查看提取文本
                  </v-btn>
                </div>
              </div>
              <div v-if="!originalFiles.length" class="empty-state">暂无原始文件</div>
            </div>
          </v-card>
        </v-col>

        <v-col cols="12" lg="6">
          <v-card class="glass-card preview-panel" rounded="xl" elevation="0">
            <div class="card-title d-flex align-center justify-space-between">
              <span>{{ requestType === 'resource' ? '资源检测概览' : '图片工作区' }}</span>
              <v-chip variant="tonal" color="primary">{{ requestType === 'resource' ? resourceTaskTypeText : `${currentImageIndex + 1} / ${images.length || 0}` }}</v-chip>
            </div>

            <div v-if="requestType === 'image'" class="image-stage">
              <div class="image-strip">
                <button
                  v-for="(image, index) in images"
                  :key="image.img_id"
                  class="thumb-btn"
                  :class="{ active: currentImageIndex === index }"
                  @click="handleImageSelect(index)"
                >
                  <img :src="getImageUrl(image.img_url)" alt="thumbnail" />
                </button>
              </div>

              <div class="stage-main">
                <div class="stage-frame">
                  <img v-if="currentImage" :src="getImageUrl(currentImage.img_url)" alt="preview" class="stage-image" />
                  <div v-else class="empty-state">暂无图片</div>
                  <div class="stage-nav">
                    <v-btn icon="mdi-chevron-left" variant="flat" @click="handlePrevImage" :disabled="currentImageIndex <= 0" />
                    <v-btn icon="mdi-chevron-right" variant="flat" @click="handleNextImage" :disabled="currentImageIndex >= images.length - 1" />
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="resource-stage">
              <div class="resource-hero">
                <div>
                  <div class="resource-kicker">{{ primaryMetricLabel }}</div>
                  <div class="resource-value">{{ primaryMetricValue }}</div>
                </div>
                <v-chip :color="resourceVerdictColor" variant="tonal">{{ resourceVerdictText }}</v-chip>
              </div>
              <div class="resource-summary">
                {{ resourceSummaryText }}
              </div>
              <div class="resource-overview-grid">
                <div v-for="item in overviewRows" :key="`resource-${item.label}`" class="resource-overview-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
            </div>
          </v-card>
        </v-col>

        <v-col cols="12" lg="3">
          <v-card class="glass-card side-panel" rounded="xl" elevation="0">
            <div class="card-title d-flex align-center justify-space-between">
              <span>审核员进度</span>
              <v-chip variant="tonal" color="secondary">{{ reviewers.length }} 人</v-chip>
            </div>
            <div class="review-list">
              <template v-if="reviewers.length">
                <button
                  class="reviewer-card"
                  v-for="review in reviewers"
                  :key="review.id"
                  :class="{ inactive: review.status !== 'completed', 'resource-reviewer-card': requestType === 'resource' }"
                  @click="requestType === 'image' && review.status === 'completed' && handleViewDetail(review)"
                >
                  <div class="reviewer-avatar">
                    <img v-if="review.avatar" :src="getImageUrl(review.avatar)" alt="avatar" />
                    <span v-else>{{ review.username.charAt(0) }}</span>
                  </div>
                  <div class="reviewer-body">
                    <div class="reviewer-name">{{ review.username }}</div>
                    <div class="reviewer-result-row">
                      <v-chip size="small" variant="tonal" :color="review.status === 'completed' ? 'teal' : 'amber'">
                        {{ review.status === 'completed' ? '已完成' : '进行中' }}
                      </v-chip>
                      <span>{{ review.completed_count }}/{{ review.total_count }}</span>
                    </div>
                    <div v-if="requestType === 'resource' && review.status === 'completed'" class="resource-review-summary">
                      <v-chip size="small" variant="tonal" :color="resourceDecisionColor(review.final_decision)">
                        {{ resourceDecisionText(review.final_decision) }}
                      </v-chip>
                      <div class="review-comment">{{ review.comment || '暂无评价原因' }}</div>
                      <div v-if="review.steps?.length" class="review-steps">
                        <span v-for="(step, stepIndex) in review.steps" :key="`${review.id}-step-${stepIndex}`">
                          {{ step }}
                        </span>
                      </div>
                    </div>
                  </div>
                  <v-icon v-if="requestType === 'image'" size="18">mdi-chevron-right</v-icon>
                </button>
              </template>
              <div v-else class="empty-state">暂无人工审核结果</div>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <v-dialog v-model="showDetailDialog" fullscreen :scrim="false" transition="dialog-bottom-transition">
      <v-card>
        <v-toolbar color="primary" theme="dark">
          <v-btn icon @click="showDetailDialog = false"><v-icon>mdi-close</v-icon></v-btn>
          <v-toolbar-title>检测详情</v-toolbar-title>
        </v-toolbar>
        <result-component
          v-if="showDetailDialog"
          :task-id="taskId === null ? undefined : String(taskId)"
          :imageUrl="getImageUrl(images[currentImageIndex]?.img_url || '')"
          :reasons="reasons"
          :result="result"
          :scores="scores"
          :ai_detection="aiDetection"
          :annotations="annotations"
        />
      </v-card>
    </v-dialog>

    <v-dialog v-model="previewDialog" max-width="1100">
      <v-card>
        <v-toolbar flat>
          <v-toolbar-title>{{ previewTitle }}</v-toolbar-title>
          <v-spacer />
          <v-btn icon @click="closePreviewDialog"><v-icon>mdi-close</v-icon></v-btn>
        </v-toolbar>
        <v-card-text>
          <v-alert v-if="previewError" type="warning" variant="tonal" class="mb-4">{{ previewError }}</v-alert>
          <v-progress-linear v-if="previewLoading" indeterminate color="primary" class="mb-4" />
          <pre v-if="previewText" class="text-block">{{ previewText }}</pre>
          <iframe v-else-if="previewUrl" :src="previewUrl" class="file-iframe" title="源文件预览" />
          <div v-else-if="!previewLoading" class="empty-state">当前文件无法预览，请下载查看源文件。</div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-if="requestType === 'resource'" v-model="showExtractDialog" max-width="900">
      <v-card>
        <v-toolbar flat>
          <v-toolbar-title>{{ extractDialogTitle || '提取文本' }}</v-toolbar-title>
          <v-spacer />
          <v-btn icon @click="showExtractDialog = false"><v-icon>mdi-close</v-icon></v-btn>
        </v-toolbar>
        <v-card-text style="max-height:70vh; overflow:auto;">
          <v-progress-linear v-if="extractLoading" indeterminate color="primary" class="mb-4" />
          <v-alert v-if="extractError" type="warning" variant="tonal" class="mb-4">{{ extractError }}</v-alert>
          <pre v-if="extractedText" class="text-block">{{ extractedText }}</pre>
          <div v-else-if="!extractLoading" class="empty-state">无提取文本</div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ResultComponent from '@/components/result.vue'
import publisher from '@/api/publisher'
import uploadApi from '@/api/upload'
import { useSnackbarStore } from '@/stores/snackbar'

interface RouteParams {
  review_request_id: string
}

interface ImageItem {
  img_id: number
  img_url: string
}

interface ReviewerItem {
  id: number
  username: string
  avatar: string
  status: 'undo' | 'completed'
  total_count: number
  completed_count: number
  review_time?: string | null
  final_decision?: string | null
  comment?: string
  steps?: string[]
}

interface OriginalFileItem {
  id?: number
  file_id?: number
  file_name: string
  resource_type: string
  file_type: string
  file_url?: string | null
}

interface DimensionItem {
  method: string
  probability: number
}

interface OverviewRow {
  label: string
  value: string
}

const router = useRouter()
const route = useRoute()
const snackbar = useSnackbarStore()

const reviewRequestId = computed(() => Number((route.params as RouteParams).review_request_id))

const taskId = ref<number | null>(null)
const requestType = ref<'image' | 'resource'>('image')
const resourceTaskType = ref<'paper' | 'review'>('paper')
const resourceResults = ref<any>({})
const combinedReport = ref('')
const images = ref<ImageItem[]>([])
const originalFiles = ref<OriginalFileItem[]>([])
const currentImageIndex = ref(0)
const done = ref(0)
const process = ref(0)
const aiDetection = ref(0)
const reviewers = ref<ReviewerItem[]>([])
const reasons = ref<string[]>([])
const result = ref(false)
const scores = ref<number[]>([])
const annotations = ref<Array<Array<{ points: { x: number; y: number }[]; color: string }>>>([])
const detectionResults = ref<DimensionItem[]>([])

const previewDialog = ref(false)
const previewTitle = ref('')
const previewUrl = ref('')
const previewText = ref('')
const previewLoading = ref(false)
const previewError = ref('')
const previewObjectUrl = ref('')
const extractedText = ref('')
const extractDialogTitle = ref('')
const extractLoading = ref(false)
const extractError = ref('')
const showExtractDialog = ref(false)
const showDetailDialog = ref(false)

const normalizeLevel = (level?: string | null) => String(level || '').toLowerCase()

const levelText = (level?: string | null) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high' || normalized === 'relevant') return '高'
  if (normalized === 'medium') return '中'
  if (normalized === 'low' || normalized === 'weak_match') return '低'
  return '未知'
}

const riskLevelColor = (level?: string | null) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high') return 'error'
  if (normalized === 'medium') return 'warning'
  if (normalized === 'low') return 'success'
  return 'grey'
}

const statusText = computed(() => {
  if (process.value === 0 && done.value === 0) return '待审核'
  if (process.value > 0) return '审核中'
  return '已完成'
})

const progressPercent = computed(() => {
  const total = done.value + process.value
  return total > 0 ? (done.value / total) * 100 : 0
})

const currentImage = computed(() => images.value[currentImageIndex.value] || null)

const resourceTaskTypeText = computed(() => resourceTaskType.value === 'review' ? 'Review 检测' : '论文检测')

const paperOverallEvaluation = computed(() => resourceResults.value?.overall_evaluation || {})
const reviewOverallEvaluation = computed(() => (
  resourceResults.value?.review_analysis_results?.overall
  || resourceResults.value?.overall_evaluation
  || {}
))

const paperRiskScore = computed(() => {
  const rawScore = Number(paperOverallEvaluation.value?.risk_score || 0)
  return rawScore > 1 ? rawScore / 100 : rawScore
})

const paperAigcRate = computed(() => {
  const paragraphs = Array.isArray(resourceResults.value?.paragraph_results)
    ? resourceResults.value.paragraph_results
    : []
  const probabilities = paragraphs
    .map((item: any) => Number(item?.probability))
    .filter((value: number) => Number.isFinite(value))
  if (!probabilities.length) return paperRiskScore.value
  return probabilities.reduce((sum: number, value: number) => sum + value, 0) / probabilities.length
})

const reviewVerdict = computed(() => {
  const explicitLabel = String(reviewOverallEvaluation.value?.qualification_label || '').toLowerCase()
  if (['qualified', 'attention', 'unqualified', 'unavailable'].includes(explicitLabel)) {
    if (explicitLabel === 'qualified') return 'pass'
    if (explicitLabel === 'unqualified') return 'suspicious'
    if (explicitLabel === 'unavailable') return 'unavailable'
    return 'attention'
  }
  if (reviewOverallEvaluation.value?.source === 'api_unavailable') return 'unavailable'
  const templateLevel = normalizeLevel(reviewOverallEvaluation.value?.template_like_level)
  const wrongnessLevel = normalizeLevel(reviewOverallEvaluation.value?.wrongness_level)
  const relevanceLevel = normalizeLevel(reviewOverallEvaluation.value?.relevance_level)
  if (templateLevel === 'high' || wrongnessLevel === 'high') return 'suspicious'
  if (relevanceLevel === 'low' || relevanceLevel === 'weak_match') return 'suspicious'
  if (templateLevel === 'medium' || wrongnessLevel === 'medium' || relevanceLevel === 'medium') return 'attention'
  if (templateLevel === 'unknown' || wrongnessLevel === 'unknown' || relevanceLevel === 'unknown') return 'attention'
  return 'pass'
})

const primaryMetricValue = computed(() => {
  if (requestType.value === 'image') return formatNumber(aiDetection.value)
  if (resourceTaskType.value === 'paper') return formatNumber(paperAigcRate.value)
  return resourceVerdictText.value
})

const primaryMetricLabel = computed(() => {
  if (requestType.value === 'image') return 'AI 判定为假'
  if (resourceTaskType.value === 'paper') return '整体 AIGC 率'
  return 'Review 综合结论'
})

const taskFocusLabel = computed(() => {
  if (requestType.value === 'image') return '当前图片'
  return '任务类型'
})

const taskFocusValue = computed(() => {
  if (requestType.value === 'image') return `${currentImageIndex.value + 1} / ${images.value.length || 0}`
  return resourceTaskTypeText.value
})

const resourceVerdictText = computed(() => {
  if (resourceTaskType.value === 'paper') {
    const riskLevel = normalizeLevel(paperOverallEvaluation.value?.risk_level)
    if (riskLevel === 'high') return '高风险'
    if (riskLevel === 'medium') return '中风险'
    if (riskLevel === 'low') return '低风险'
    return '风险未知'
  }
  if (reviewVerdict.value === 'suspicious') return '可疑'
  if (reviewVerdict.value === 'attention') return '需关注'
  if (reviewVerdict.value === 'unavailable') return '分析不可用'
  if (reviewOverallEvaluation.value?.qualification_text) return reviewOverallEvaluation.value.qualification_text
  return '通过'
})

const resourceVerdictColor = computed(() => {
  if (resourceTaskType.value === 'paper') return riskLevelColor(paperOverallEvaluation.value?.risk_level)
  if (reviewVerdict.value === 'suspicious') return 'error'
  if (reviewVerdict.value === 'attention') return 'warning'
  if (reviewVerdict.value === 'unavailable') return 'info'
  return 'success'
})

const resourceSummaryText = computed(() => {
  if (requestType.value !== 'resource') return ''
  const summary = resourceTaskType.value === 'paper'
    ? paperOverallEvaluation.value?.summary
    : reviewOverallEvaluation.value?.summary
  return summary || combinedReport.value || '暂无综合说明'
})

const overviewRows = computed<OverviewRow[]>(() => {
  if (requestType.value === 'image') {
    return detectionResults.value.map((dimension, index) => ({
      label: convert(index),
      value: dimension.probability.toFixed(2),
    }))
  }

  if (resourceTaskType.value === 'paper') {
    const confirmedCount = Array.isArray(resourceResults.value?.confirmed_ai_paragraphs)
      ? resourceResults.value.confirmed_ai_paragraphs.length
      : 0
    const suspiciousCount = Array.isArray(resourceResults.value?.suspicious_paragraphs)
      ? resourceResults.value.suspicious_paragraphs.length
      : 0
    return [
      { label: '风险等级', value: resourceVerdictText.value },
      { label: '整体AIGC率', value: formatNumber(paperAigcRate.value) },
      { label: '风险评分', value: formatNumber(paperRiskScore.value) },
      { label: '疑似段落', value: `${suspiciousCount} 段` },
      { label: '基本确认 AI', value: `${confirmedCount} 段` },
    ]
  }

  return [
    { label: '综合结论', value: resourceVerdictText.value },
    { label: '模板化倾向', value: levelText(reviewOverallEvaluation.value?.template_like_level) },
    { label: '内容错误风险', value: levelText(reviewOverallEvaluation.value?.wrongness_level) },
    { label: '与论文相关度', value: levelText(reviewOverallEvaluation.value?.relevance_level) },
  ]
})

const goBack = () => router.back()

const loadRequestDetail = async () => {
  if (route.query.request_type === 'resource') {
    const resourceResponse = (await publisher.getRequestDetail({ review_request_id: reviewRequestId.value, request_type: 'resource' })).data
    requestType.value = resourceResponse.request_type || 'resource'
    return resourceResponse
  }

  try {
    const imageResponse = (await publisher.getRequestDetail({ review_request_id: reviewRequestId.value, request_type: 'image' })).data
    requestType.value = imageResponse.request_type || 'image'
    return imageResponse
  } catch {
    const resourceResponse = (await publisher.getRequestDetail({ review_request_id: reviewRequestId.value, request_type: 'resource' })).data
    requestType.value = resourceResponse.request_type || 'resource'
    return resourceResponse
  }
}

const getImageUrl = (url: string) => `${import.meta.env.VITE_API_URL || ''}${url}`

const getFileUrl = (file: OriginalFileItem) => {
  if (!file.file_url) return ''
  return /^https?:\/\//.test(file.file_url) ? file.file_url : `${import.meta.env.VITE_API_URL || ''}${file.file_url}`
}

const revokePreviewObjectUrl = () => {
  if (previewObjectUrl.value) {
    URL.revokeObjectURL(previewObjectUrl.value)
    previewObjectUrl.value = ''
  }
}

const closePreviewDialog = () => {
  previewDialog.value = false
  revokePreviewObjectUrl()
}

const setPreviewUrl = (url: string, isObjectUrl = false) => {
  revokePreviewObjectUrl()
  previewUrl.value = url
  previewObjectUrl.value = isObjectUrl ? url : ''
}

const formatNumber = (value: number) => `${(value * 100).toFixed(2)}%`

const convert = (index: number) => {
  const labels = ['高斯模糊', '亮度/对比度调节', '智能修复', '暴力覆盖', '同图复制', '重叠切割', '跨图拼接']
  return labels[index] || `维度${index + 1}`
}

const resourceDecisionText = (decision?: string | null) => {
  const normalized = String(decision || '')
  const labels: Record<string, string> = {
    high_ai_risk: '疑似AIGC风险高',
    medium_ai_risk: '存在一定AIGC风险',
    low_ai_risk: '整体风险较低',
    relevant: '评审内容高度相关',
    partially_relevant: '评审内容部分相关',
    weak_relevance: '评审内容相关性较低',
  }
  return labels[normalized] || '未给出结论'
}

const resourceDecisionColor = (decision?: string | null) => {
  const normalized = String(decision || '')
  if (['high_ai_risk', 'weak_relevance'].includes(normalized)) return 'error'
  if (['medium_ai_risk', 'partially_relevant'].includes(normalized)) return 'warning'
  if (['low_ai_risk', 'relevant'].includes(normalized)) return 'success'
  return 'grey'
}

const downloadFile = (file: OriginalFileItem) => {
  const url = getFileUrl(file)
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = file.file_name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const loadFileTextPreview = async (file: OriginalFileItem, target: 'preview' | 'extract') => {
  const fileId = file.file_id || file.id
  if (!fileId) {
    snackbar.showMessage('文件缺少ID，无法获取提取文本', 'error')
    return
  }

  const isPreview = target === 'preview'
  if (isPreview) {
    previewDialog.value = true
    previewTitle.value = file.file_name
    setPreviewUrl('')
    previewText.value = ''
    previewError.value = ''
    previewLoading.value = true
  } else {
    showExtractDialog.value = true
    extractDialogTitle.value = `提取文本 - ${file.file_name}`
    extractLoading.value = true
    extractError.value = ''
    extractedText.value = ''
  }

  try {
    const response = await uploadApi.getResourceTextPreview(fileId, taskId.value)
    const textContent = response.data?.text_content || ''
    if (isPreview) {
      previewText.value = textContent
    } else {
      extractedText.value = textContent
    }
    if (response.data?.text_truncated) {
      const message = '文件较长，当前仅展示前 6000000 字。'
      if (isPreview) previewError.value = message
      else extractError.value = message
    }
    if (!textContent) {
      const message = '当前文件暂无可展示文本。'
      if (isPreview) previewError.value = previewError.value || message
      else extractError.value = extractError.value || message
    }
  } catch (error: any) {
    const message = error?.response?.data?.message || '获取提取文本失败。'
    if (isPreview) previewError.value = message
    else extractError.value = message
  } finally {
    if (isPreview) previewLoading.value = false
    else extractLoading.value = false
  }
}

const previewFile = async (file: OriginalFileItem) => {
  previewDialog.value = true
  previewTitle.value = file.file_name
  setPreviewUrl('')
  previewText.value = ''
  previewError.value = ''
  previewLoading.value = true

  const fileId = file.file_id || file.id
  if (!fileId) {
    previewLoading.value = false
    previewError.value = '当前文件缺少ID，无法预览源文件。'
    return
  }

  try {
    let response
    try {
      response = await uploadApi.getResourceFilePreview(fileId)
    } catch {
      response = await uploadApi.downloadResourceFile(fileId)
    }
    const blob = response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: file.file_type || 'application/octet-stream' })
    setPreviewUrl(URL.createObjectURL(blob), true)
  } catch (error: any) {
    previewError.value = error?.response?.data?.message || '当前文件无法预览，请下载查看源文件。'
  } finally {
    previewLoading.value = false
  }
}

const openExtractDialog = async (file: OriginalFileItem) => {
  if (requestType.value !== 'resource') {
    return
  }
  await loadFileTextPreview(file, 'extract')
}

const fetchDetectionResults = async () => {
  if (!currentImage.value) return
  try {
    const detectionId = (await publisher.getDetectionID({ img_id: currentImage.value.img_id })).data.detection_result_id
    detectionResults.value = (await publisher.getSingleImageResult(detectionId)).data.sub_methods || []
  } catch {
    snackbar.showMessage('获取检测结果失败', 'error')
  }
}

const fetchReviewDetail = async (review: ReviewerItem) => {
  if (!currentImage.value) return
  try {
    const response = (await publisher.getImageReviewDetail({
      review_request_id: reviewRequestId.value,
      img_id: currentImage.value.img_id,
      reviewer_id: review.id,
    })).data
    reasons.value = response.reasons || []
    result.value = response.result
    scores.value = response.scores || []
    annotations.value = response.points || []
  } catch {
    snackbar.showMessage('获取人工审核详情失败', 'error')
  }
}

const handleImageSelect = async (index: number) => {
  currentImageIndex.value = index
  await fetchDetectionResults()
}

const handlePrevImage = () => {
  if (currentImageIndex.value > 0) handleImageSelect(currentImageIndex.value - 1)
}

const handleNextImage = () => {
  if (currentImageIndex.value < images.value.length - 1) handleImageSelect(currentImageIndex.value + 1)
}

const handleViewDetail = async (review: ReviewerItem) => {
  await fetchReviewDetail(review)
  showDetailDialog.value = true
}

const handleDownloadReport = async () => {
  try {
    const response = await publisher.downloadReviewReport({ review_request_id: reviewRequestId.value })
    if (!(response.data instanceof Blob)) {
      snackbar.showMessage('下载失败：未收到文件数据', 'error')
      return
    }
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `人工审核报告_${reviewRequestId.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    snackbar.showMessage('报告下载成功', 'success')
  } catch {
    snackbar.showMessage('报告下载失败', 'error')
  }
}

onMounted(async () => {
  try {
    const response = await loadRequestDetail()
    done.value = response.status?.done || 0
    process.value = response.status?.process || 0
    aiDetection.value = response.ai_detection_result?.confidence_score || 0
    taskId.value = response.task_id || null
    resourceTaskType.value = response.task_type || 'paper'
    resourceResults.value = response.extracted_text || {}
    combinedReport.value = response.combined_report || ''
    images.value = response.images || []
    originalFiles.value = response.original_files || []
    reviewers.value = response.reviewers || []
    if (response.extracted_text) {
      extractedText.value = typeof response.extracted_text === 'string'
        ? response.extracted_text
        : JSON.stringify(response.extracted_text, null, 2)
    }
    if (images.value.length > 0) {
      currentImageIndex.value = 0
      await fetchDetectionResults()
    }
  } catch {
    snackbar.showMessage('获取人工审核结果失败', 'error')
  }
})

onUnmounted(() => {
  revokePreviewObjectUrl()
})
</script>

<style scoped>
.publisher-progress-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(56, 189, 248, 0.12), transparent 28%),
    radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.10), transparent 24%),
    linear-gradient(180deg, rgba(248, 250, 252, 1), rgba(241, 245, 249, 1));
}

.page-shell {
  max-width: 1600px;
  margin: 0 auto;
}

.hero-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 28px 28px 24px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
  margin-bottom: 20px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.55);
  margin-bottom: 10px;
}

.hero-bar h1 {
  font-size: clamp(2rem, 3vw, 3rem);
  line-height: 1.05;
  margin: 0 0 10px;
  color: rgb(15, 23, 42);
}

.hero-bar p {
  margin: 0;
  color: rgba(15, 23, 42, 0.72);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: flex-end;
}

.glass-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(18px);
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.progress-card,
.summary-card,
.side-panel,
.preview-panel {
  height: 100%;
  padding: 20px;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  color: rgb(15, 23, 42);
  margin-bottom: 16px;
}

.progress-ring {
  width: 170px;
  height: 170px;
  border-radius: 50%;
  margin: 0 auto;
  display: grid;
  place-items: center;
  border: 10px solid rgba(59, 130, 246, 0.15);
  box-shadow: inset 0 0 0 8px rgba(255, 255, 255, 0.8);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 250, 252, 0.85));
}

.progress-value {
  font-size: 2.2rem;
  font-weight: 800;
  color: rgb(29, 78, 216);
  text-align: center;
}

.progress-label {
  font-size: 0.95rem;
  text-align: center;
  color: rgba(15, 23, 42, 0.6);
}

.progress-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 18px;
}

.summary-list,
.file-list,
.review-list {
  display: grid;
  gap: 12px;
}

.summary-row,
.file-item,
.reviewer-card {
  border-radius: 18px;
  padding: 14px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.summary-row span {
  color: rgba(15, 23, 42, 0.64);
}

.dimension-mini {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.dimension-mini:last-child {
  border-bottom: none;
}

.file-main {
  margin-bottom: 10px;
}

.file-name,
.reviewer-name {
  font-weight: 700;
  color: rgb(15, 23, 42);
}

.file-meta,
.reviewer-result {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.6);
}

.file-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reviewer-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
}

.reviewer-card.inactive {
  opacity: 0.72;
  cursor: default;
}

.reviewer-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background: linear-gradient(135deg, rgb(59, 130, 246), rgb(14, 165, 233));
  color: white;
  display: grid;
  place-items: center;
  font-weight: 700;
}

.reviewer-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.reviewer-body {
  flex: 1;
  min-width: 0;
}

.reviewer-result-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
  font-size: 12px;
  color: rgba(15, 23, 42, 0.62);
}

.reviewer-result.fake {
  color: rgb(220, 38, 38);
}

.reviewer-result.real {
  color: rgb(22, 163, 74);
}

.image-stage {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 14px;
}

.image-strip {
  max-height: 74vh;
  overflow-y: auto;
  display: grid;
  gap: 10px;
  padding-right: 4px;
}

.thumb-btn {
  width: 84px;
  height: 84px;
  border: 2px solid transparent;
  border-radius: 14px;
  overflow: hidden;
  padding: 0;
  background: transparent;
}

.thumb-btn.active {
  border-color: rgb(29, 78, 216);
  box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.12);
}

.thumb-btn img,
.stage-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.stage-main {
  min-width: 0;
}

.stage-frame {
  position: relative;
  height: min(68vh, 760px);
  border-radius: 24px;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(241,245,249,0.95));
  border: 1px solid rgba(148, 163, 184, 0.2);
  display: grid;
  place-items: center;
}

.stage-image {
  object-fit: contain;
}

.stage-nav {
  position: absolute;
  inset: auto 16px 16px auto;
  display: flex;
  gap: 10px;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 140px;
  color: rgba(15, 23, 42, 0.58);
}

.empty-state.compact {
  min-height: 64px;
}

.resource-stage {
  display: grid;
  gap: 18px;
}

.resource-hero {
  min-height: 220px;
  border-radius: 24px;
  padding: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background:
    radial-gradient(circle at 20% 20%, rgba(14, 165, 233, 0.18), transparent 34%),
    linear-gradient(135deg, rgba(241, 245, 249, 0.95), rgba(255, 255, 255, 0.92));
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.resource-kicker {
  font-size: 13px;
  color: rgba(15, 23, 42, 0.62);
  margin-bottom: 8px;
}

.resource-value {
  font-size: clamp(2.6rem, 5vw, 4.5rem);
  font-weight: 850;
  color: rgb(15, 23, 42);
  line-height: 1;
}

.resource-summary {
  border-radius: 18px;
  padding: 16px;
  color: rgba(15, 23, 42, 0.72);
  line-height: 1.7;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.resource-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.resource-overview-item {
  border-radius: 18px;
  padding: 14px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.resource-overview-item span {
  display: block;
  color: rgba(15, 23, 42, 0.6);
  font-size: 12px;
  margin-bottom: 6px;
}

.resource-overview-item strong {
  color: rgb(15, 23, 42);
  font-size: 18px;
}

.resource-reviewer-card {
  align-items: flex-start;
}

.resource-review-summary {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.review-comment {
  color: rgba(15, 23, 42, 0.74);
  line-height: 1.55;
  word-break: break-word;
}

.review-steps {
  display: grid;
  gap: 4px;
}

.review-steps span {
  font-size: 12px;
  color: rgba(15, 23, 42, 0.62);
  padding-left: 10px;
  border-left: 2px solid rgba(59, 130, 246, 0.28);
}

.file-iframe {
  width: 100%;
  min-height: 70vh;
  border: 0;
  border-radius: 16px;
}

.text-block {
  max-height: 60vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  line-height: 1.65;
  margin: 0;
}

@media (max-width: 1280px) {
  .image-stage {
    grid-template-columns: 1fr;
  }

  .image-strip {
    grid-template-columns: repeat(auto-fill, minmax(84px, 84px));
    grid-auto-flow: column;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .stage-frame {
    height: min(60vh, 640px);
  }
}

@media (max-width: 960px) {
  .hero-bar {
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}
</style>
