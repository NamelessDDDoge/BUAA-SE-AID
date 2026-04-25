<template>
  <v-container class="mt-8">
    <v-row>
      <v-col cols="12">
        <v-card class="mb-8 pa-6" elevation="2" rounded="lg">
          <v-row>
            <v-col cols="12" md="4" class="d-flex justify-center align-center">
              <v-progress-circular
                :model-value="circleValue"
                :size="160"
                :width="12"
                :color="circleColor"
              >
                <div class="text-center">
                  <div class="text-h5 font-weight-bold">{{ circleMainText }}</div>
                  <div class="text-caption">{{ circleSubText }}</div>
                </div>
              </v-progress-circular>
            </v-col>

            <v-col cols="12" md="8">
              <div class="text-h6 font-weight-bold mb-4">{{ detailTitle }}</div>
              <div class="d-flex flex-wrap ga-3 mb-4">
                <v-chip :color="statusColor" size="small">{{ statusLabel }}</v-chip>
                <v-chip size="small" color="grey-lighten-2">任务 #{{ task.task_id }}</v-chip>
                <v-chip size="small" color="grey-lighten-2">{{ totalCountLabel }} {{ totalCount }}</v-chip>
                <v-chip v-if="isPaper" size="small" color="primary" variant="tonal">
                  基本确认AI段落 {{ paperConfirmedParagraphs.length }}
                </v-chip>
              </div>

              <div class="text-body-2 text-medium-emphasis mb-2">{{ task.result_summary || defaultSummary }}</div>
              <div v-if="task.error_message" class="text-body-2 text-error mb-2">{{ task.error_message }}</div>
              <div class="text-body-2 text-medium-emphasis mb-4">{{ descriptionText }}</div>

              <v-alert
                v-if="isPaper && paperOverallEvaluation?.summary"
                type="info"
                variant="tonal"
                class="mb-4"
              >
                <div class="font-weight-medium mb-1">
                  整篇综合评价（{{ paperOverallEvaluation.risk_level || 'unknown' }}）
                </div>
                <div>{{ paperOverallEvaluation.summary }}</div>
              </v-alert>

              <div class="d-flex flex-wrap ga-3">
                <v-btn color="secondary" variant="elevated" :disabled="task.status !== 'completed'" @click="$emit('download')">
                  下载报告
                </v-btn>
                <v-btn
                  color="primary"
                  variant="elevated"
                  :disabled="!canSubmit"
                  @click="submitReview"
                >
                  申请人工审核
                </v-btn>
              </div>
            </v-col>
          </v-row>
        </v-card>

        <v-alert v-if="task.resource_split_note" type="warning" variant="tonal" class="mb-6">
          {{ task.resource_split_note }}
        </v-alert>

        <v-card v-if="task.resource_files?.length" class="mb-6" elevation="2" rounded="lg">
          <v-card-title class="text-h6">上传文件</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="file in task.resource_files" :key="file.file_id">
                <v-list-item-title>{{ file.file_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ file.resource_type }} · {{ formatFileSize(file.file_size) }}</v-list-item-subtitle>
                <template #append>
                  <div class="d-flex ga-2">
                    <v-btn size="small" variant="text" prepend-icon="mdi-eye-outline" @click="previewFile(file)">预览</v-btn>
                    <v-btn size="small" variant="text" prepend-icon="mdi-download" :disabled="!file.file_url" @click="downloadFile(file)">下载</v-btn>
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>

        <v-card v-if="isPaper" class="mb-6" elevation="2" rounded="lg">
          <v-card-title class="text-h6">论文段落统计与整篇评价</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">段落总数</div>
                <div class="text-h5 font-weight-bold">{{ paperParagraphs.length }}</div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">疑似 AI 段落</div>
                <div class="text-h5 font-weight-bold text-error">{{ paperSuspiciousParagraphs.length }}</div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">基本确认 AI 段落</div>
                <div class="text-h5 font-weight-bold" :class="paperConfirmedParagraphs.length ? 'text-warning' : 'text-success'">
                  {{ paperConfirmedParagraphs.length }}
                </div>
              </v-col>
            </v-row>

            <v-divider class="my-4" />

            <div class="text-subtitle-2 mb-2">整篇论文综合评价</div>
            <v-alert
              :type="paperOverallRiskLevel === 'high' ? 'error' : paperOverallRiskLevel === 'medium' ? 'warning' : 'success'"
              variant="tonal"
            >
              <div class="mb-1"><strong>风险等级：</strong>{{ paperOverallRiskLevelText }}</div>
              <div class="mb-1"><strong>风险评分：</strong>{{ paperOverallScore }}</div>
              <div><strong>总结：</strong>{{ paperOverallSummary }}</div>
            </v-alert>
          </v-card-text>
        </v-card>

        <v-card v-if="reviewMode" class="mb-6" elevation="2" rounded="lg">
          <v-card-title class="text-h6">Review 审查摘要</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">模板化倾向</div>
                <div class="text-h5 font-weight-bold">{{ reviewOverallLevelText(reviewOverallEvaluation?.template_like_level) }}</div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">内容错误风险</div>
                <div class="text-h5 font-weight-bold">{{ reviewOverallLevelText(reviewOverallEvaluation?.wrongness_level) }}</div>
              </v-col>
              <v-col cols="12" md="4">
                <div class="text-caption text-medium-emphasis">与论文相关度</div>
                <div class="text-h5 font-weight-bold">{{ reviewOverallLevelText(reviewOverallEvaluation?.relevance_level) }}</div>
              </v-col>
            </v-row>

            <v-divider class="my-4" />

            <v-alert type="info" variant="tonal">
              <div class="mb-1"><strong>总结：</strong>{{ reviewOverallEvaluation?.summary || '暂无总结' }}</div>
              <div v-if="(reviewOverallEvaluation?.key_findings || []).length" class="mt-2">
                <strong>关键发现：</strong>{{ (reviewOverallEvaluation?.key_findings || []).join('；') }}
              </div>
            </v-alert>
          </v-card-text>
        </v-card>

        <v-row v-if="!isPaper && !reviewMode">
          <v-col v-if="showFakeCard" cols="12" :md="isPaper || reviewMode ? 12 : 6">
            <v-card elevation="2" rounded="lg" class="h-100">
              <v-card-title class="d-flex justify-space-between align-center">
                <div class="d-flex align-center ga-2">
                  <v-icon color="error">mdi-alert-circle</v-icon>
                  <span class="text-h6">{{ fakeSectionTitle }}</span>
                  <v-chip color="error" size="small">
                    {{
                      reviewMode
                        ? fakeFiles.length
                        : isPaper
                          ? fakeCount
                          : `${selectedFakeCount}/${fakeFiles.length}`
                    }}
                  </v-chip>
                </div>
                <v-btn v-if="!reviewMode && !isPaper" size="small" variant="text" color="error" @click="toggleSelect(fakeFiles)">
                  {{ isAllSelected(fakeFiles) ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text>
                <v-list v-if="isPaper && paperSuspiciousParagraphs.length" lines="two">
                  <v-list-item v-for="paragraph in paperSuspiciousParagraphs" :key="`sus-${paragraph.paragraph_index}`">
                    <v-list-item-title>
                      第 {{ (paragraph.paragraph_index ?? 0) + 1 }} 段 · AIGC率 {{ ((paragraph.probability || 0) * 100).toFixed(1) }}%
                    </v-list-item-title>
                    <v-list-item-subtitle>{{ paragraph.forgery_reason || paragraph.text || '-' }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
                <v-list v-else-if="!isPaper && fakeFiles.length" lines="two">
                  <v-list-item v-for="file in fakeFiles" :key="file.file_id">
                    <template v-if="!reviewMode" #prepend>
                      <v-checkbox-btn v-model="selectedFileIds" :value="file.file_id" color="error" />
                    </template>
                    <v-list-item-title>{{ file.file_name }}</v-list-item-title>
                    <v-list-item-subtitle>{{ file.resource_type }} · {{ formatFileSize(file.file_size) }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
                <div v-else class="text-center text-medium-emphasis py-6">{{ emptyFakeText }}</div>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col v-if="showNormalCard" cols="12" :md="isPaper || reviewMode ? 12 : 6">
            <v-card elevation="2" rounded="lg" class="h-100">
              <v-card-title class="d-flex justify-space-between align-center">
                <div class="d-flex align-center ga-2">
                  <v-icon color="success">mdi-check-circle</v-icon>
                  <span class="text-h6">{{ normalSectionTitle }}</span>
                  <v-chip color="success" size="small">
                    {{
                      reviewMode
                        ? effectiveNormalFiles.length
                        : isPaper
                          ? paperCleanParagraphs.length
                          : `${selectedNormalCount}/${effectiveNormalFiles.length}`
                    }}
                  </v-chip>
                </div>
                <v-btn v-if="!reviewMode && !isPaper" size="small" variant="text" color="success" @click="toggleSelect(effectiveNormalFiles)">
                  {{ isAllSelected(effectiveNormalFiles) ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text>
                <v-list v-if="isPaper && paperCleanParagraphs.length" lines="two">
                  <v-list-item v-for="paragraph in paperCleanParagraphs" :key="`clean-${paragraph.paragraph_index}`">
                    <v-list-item-title>
                      第 {{ (paragraph.paragraph_index ?? 0) + 1 }} 段 · AIGC率 {{ ((paragraph.probability || 0) * 100).toFixed(1) }}%
                    </v-list-item-title>
                    <v-list-item-subtitle>{{ paragraph.text || '-' }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
                <v-list v-else-if="!isPaper && effectiveNormalFiles.length" lines="two">
                  <v-list-item v-for="file in effectiveNormalFiles" :key="file.file_id">
                    <template v-if="!reviewMode" #prepend>
                      <v-checkbox-btn v-model="selectedFileIds" :value="file.file_id" color="success" />
                    </template>
                    <v-list-item-title>{{ file.file_name }}</v-list-item-title>
                    <v-list-item-subtitle>{{ file.resource_type }} · {{ formatFileSize(file.file_size) }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
                <div v-else class="text-center text-medium-emphasis py-6">{{ emptyNormalText }}</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-card class="mt-6" elevation="2" rounded="lg">
          <v-card-title class="text-h6">审核配置</v-card-title>
          <v-card-text>
            <v-alert v-if="reviewMode" :type="fakeFiles.length > 0 ? 'warning' : 'success'" variant="tonal" class="mb-4">
              <template v-if="fakeFiles.length > 0">
                当前 Review 检测结果为疑似造假。选择审核员后将提交本任务全部内容进行人工审核。
              </template>
              <template v-else>
                当前 Review 检测结果为正常。选择审核员后仍可提交本任务全部内容进行人工审核。
              </template>
            </v-alert>
            <v-autocomplete
              v-model="selectedReviewers"
              :items="reviewerOptions"
              item-title="username"
              item-value="id"
              label="选择审核员"
              multiple
              chips
              closable-chips
              variant="outlined"
              hide-details
            />
            <v-textarea
              v-model="reviewReason"
              class="mt-4"
              label="申请人工审核理由"
              placeholder="请说明为什么需要人工审核"
              rows="3"
              variant="outlined"
              counter="500"
              :rules="[value => !!String(value || '').trim() || '请填写申请理由']"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>

  <v-dialog v-model="previewDialog" max-width="900">
    <v-card>
      <v-card-title class="d-flex align-center">
        <span class="text-h6">{{ previewTitle }}</span>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="previewDialog = false" />
      </v-card-title>
      <v-card-text>
        <v-alert v-if="previewError" type="warning" variant="tonal" class="mb-4">{{ previewError }}</v-alert>
        <v-progress-linear v-if="previewLoading" indeterminate color="primary" class="mb-4" />
        <pre v-else class="file-preview">{{ previewText }}</pre>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import uploadApi from '@/api/upload'

interface ResourceFile {
  file_id: number
  file_name: string
  resource_type: string
  file_type: string
  file_size: number
  file_url?: string | null
}

interface TaskDetail {
  task_id: number
  task_name: string
  task_type: 'image' | 'paper' | 'review'
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  upload_time: string
  completion_time: string | null
  result_summary?: string
  error_message?: string | null
  resource_files: ResourceFile[]
  fake_resource_files?: ResourceFile[]
  normal_resource_files?: ResourceFile[]
  pending_resource_files?: ResourceFile[]
  resource_split_note?: string | null
  results?: {
    paragraph_results?: Array<{ paragraph_index: number; label?: string; probability?: number; text?: string; forgery_reason?: string }>
    confirmed_ai_paragraphs?: Array<{ paragraph_index: number; probability?: number; reason?: string }>
    overall_evaluation?: {
      risk_score?: number
      risk_level?: string
      summary?: string
      template_like_level?: string
      wrongness_level?: string
      relevance_level?: string
      key_findings?: string[]
    }
    review_analysis_results?: {
      overall?: {
        template_like_level?: string
        wrongness_level?: string
        relevance_level?: string
        summary?: string
        key_findings?: string[]
      }
    }
  }
}

interface ReviewerOption {
  id: number
  username: string
  avatar?: string | null
}

const props = defineProps<{
  task: TaskDetail
  reviewerOptions: ReviewerOption[]
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[]; reason: string }): void
}>()

const selectedFileIds = ref<number[]>([])
const selectedReviewers = ref<number[]>([])
const reviewReason = ref('')
const previewDialog = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewText = ref('')
const previewError = ref('')

const fakeFiles = computed(() => props.task.fake_resource_files || [])
const normalFiles = computed(() => props.task.normal_resource_files || [])
const fallbackFiles = computed(() => props.task.resource_files || [])

const effectiveNormalFiles = computed(() => {
  if (fakeFiles.value.length || normalFiles.value.length) {
    return normalFiles.value
  }
  return fallbackFiles.value
})

watch(() => props.task.task_id, () => {
  selectedFileIds.value = []
  selectedReviewers.value = []
}, { immediate: true })

const isPaper = computed(() => props.task.task_type === 'paper')
const reviewMode = computed(() => props.task.task_type === 'review')
const paperParagraphs = computed(() => props.task.results?.paragraph_results || [])
const paperSuspiciousParagraphs = computed(() => paperParagraphs.value.filter(p => p.label === 'suspicious'))
const paperCleanParagraphs = computed(() => paperParagraphs.value.filter(p => p.label === 'clean'))
const paperConfirmedParagraphs = computed(() => props.task.results?.confirmed_ai_paragraphs || [])
const paperOverallEvaluation = computed(() => props.task.results?.overall_evaluation || null)
const paperOverallRiskLevel = computed(() => String(paperOverallEvaluation.value?.risk_level || 'low'))
const paperOverallRiskLevelText = computed(() => {
  if (paperOverallRiskLevel.value === 'high') return '高风险'
  if (paperOverallRiskLevel.value === 'medium') return '中风险'
  return '低风险'
})
const paperOverallScore = computed(() => Number(paperOverallEvaluation.value?.risk_score || 0))
const paperOverallSummary = computed(() => String(
  paperOverallEvaluation.value?.summary || '暂无整篇评价，建议查看段落级结果。',
))
const reviewOverallEvaluation = computed(() => props.task?.results?.review_analysis_results?.overall || props.task?.results?.overall_evaluation || null)
const reviewIsFake = computed(() => reviewMode.value && fakeFiles.value.length > 0)

const reviewOverallLevelText = (level?: string) => {
  const normalized = String(level || 'low').toLowerCase()
  if (normalized === 'high') return '高'
  if (normalized === 'medium') return '中'
  return '低'
}

const showFakeCard = computed(() => !reviewMode.value || reviewIsFake.value)
const showNormalCard = computed(() => !reviewMode.value || !reviewIsFake.value)

const detailTitle = computed(() => props.task.task_type === 'paper' ? '论文检测详情' : '同行评审 Review 检测详情')

const totalCountLabel = computed(() => props.task.task_type === 'paper' ? '段落总数' : 'Review 总数')
const fakeCountLabel = computed(() => props.task.task_type === 'paper' ? '疑似AI段落数量' : '造假 Review 数量')
const fakeSectionTitle = computed(() => props.task.task_type === 'paper' ? '疑似造假段落' : '疑似造假 Review')
const normalSectionTitle = computed(() => props.task.task_type === 'paper' ? '非疑似段落' : '正常 Review')
const emptyFakeText = computed(() => props.task.task_type === 'paper' ? '暂无疑似造假段落' : '暂无疑似造假 Review')
const emptyNormalText = computed(() => props.task.task_type === 'paper' ? '暂无非疑似段落' : '暂无正常 Review')

const defaultSummary = computed(() => props.task.task_type === 'paper' ? '论文检测任务已创建，等待系统输出完整结论。' : 'Review 检测任务已创建，等待系统输出完整结论。')

const descriptionText = computed(() => {
  if (props.task.task_type === 'paper') {
    return '展示每段 AIGC 率、疑似段落、基本确认 AI 段落与整篇综合评价，支持下载综合鉴伪报告并发起人工复核。'
  }
  return '展示 Review 文本 AIGC 概率与评审相关度检测结果，支持下载综合鉴伪报告并发起人工复核。'
})

const statusLabel = computed(() => {
  switch (props.task.status) {
    case 'pending':
      return '排队中'
    case 'in_progress':
      return '进行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '未知'
  }
})

const statusColor = computed(() => {
  switch (props.task.status) {
    case 'pending':
      return 'warning'
    case 'in_progress':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    default:
      return 'grey'
  }
})

const totalCount = computed(() => {
  if (isPaper.value) return paperParagraphs.value.length
  return fakeFiles.value.length + effectiveNormalFiles.value.length
})
const fakeCount = computed(() => {
  if (isPaper.value) return paperSuspiciousParagraphs.value.length
  return fakeFiles.value.length
})
const riskRatio = computed(() => {
  if (!totalCount.value) {
    return 0
  }
  return (fakeCount.value / totalCount.value) * 100
})

const circleValue = computed(() => reviewMode.value ? 100 : riskRatio.value)
const circleColor = computed(() => {
  if (reviewMode.value) {
    return reviewIsFake.value ? 'error' : 'success'
  }
  return 'primary'
})
const circleMainText = computed(() => {
  if (reviewMode.value) {
    return reviewIsFake.value ? '造假Review' : '正常Review'
  }
  return `${fakeCount.value}/${totalCount.value}`
})
const circleSubText = computed(() => {
  if (reviewMode.value) {
    return ''
  }
  return fakeCountLabel.value
})

const selectedFakeCount = computed(() => fakeFiles.value.filter(f => selectedFileIds.value.includes(f.file_id)).length)
const selectedNormalCount = computed(() => effectiveNormalFiles.value.filter(f => selectedFileIds.value.includes(f.file_id)).length)

const canSubmit = computed(() => {
  if (props.task.status !== 'completed') {
    return false
  }
  if (reviewMode.value) {
    return selectedReviewers.value.length > 0 && props.task.resource_files.length > 0 && reviewReason.value.trim().length > 0
  }
  if (isPaper.value) {
    return selectedReviewers.value.length > 0 && props.task.resource_files.length > 0 && reviewReason.value.trim().length > 0
  }
  return selectedReviewers.value.length > 0 && selectedFileIds.value.length > 0 && reviewReason.value.trim().length > 0
})

const isAllSelected = (files: ResourceFile[]) => {
  if (!files.length) {
    return false
  }
  return files.every(f => selectedFileIds.value.includes(f.file_id))
}

const toggleSelect = (files: ResourceFile[]) => {
  if (!files.length) {
    return
  }
  if (isAllSelected(files)) {
    selectedFileIds.value = selectedFileIds.value.filter(id => !files.some(f => f.file_id === id))
    return
  }
  const merged = new Set(selectedFileIds.value)
  files.forEach(f => merged.add(f.file_id))
  selectedFileIds.value = Array.from(merged)
}

const submitReview = () => {
  if (!canSubmit.value) {
    return
  }
  const selectedIds = reviewMode.value
    ? props.task.resource_files.map(f => f.file_id)
    : isPaper.value
      ? props.task.resource_files.map(f => f.file_id)
      : selectedFileIds.value

  emit('request-review', {
    reviewers: selectedReviewers.value,
    selected_file_ids: selectedIds,
    reason: reviewReason.value.trim(),
  })
}

const formatDateTime = (dateTime?: string | null) => {
  if (!dateTime) return ''
  const date = new Date(dateTime)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

const formatFileSize = (size: number) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`
}

const getFileUrl = (file: ResourceFile) => {
  if (!file.file_url) return ''
  if (/^https?:\/\//.test(file.file_url)) return file.file_url
  return `${import.meta.env.VITE_API_URL || ''}${file.file_url}`
}

const downloadFile = (file: ResourceFile) => {
  const url = getFileUrl(file)
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = file.file_name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const previewFile = async (file: ResourceFile) => {
  previewDialog.value = true
  previewLoading.value = true
  previewTitle.value = file.file_name
  previewText.value = ''
  previewError.value = ''
  try {
    const response = await uploadApi.getResourceTextPreview(file.file_id)
    previewText.value = response.data?.text_content || '暂无可预览文本。'
    if (response.data?.text_truncated) {
      previewError.value = '文件较长，当前仅展示前 60000 字。'
    }
  } catch (error: any) {
    previewError.value = error?.response?.data?.message || '当前文件暂不支持文本预览，请下载查看。'
  } finally {
    previewLoading.value = false
  }
}
</script>

<style scoped>
.file-preview {
  max-height: 60vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
</style>
