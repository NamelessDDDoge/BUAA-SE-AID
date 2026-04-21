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
              </div>

              <div class="text-body-2 text-medium-emphasis mb-2">{{ task.result_summary || defaultSummary }}</div>
              <div v-if="task.error_message" class="text-body-2 text-error mb-2">{{ task.error_message }}</div>
              <div class="text-body-2 text-medium-emphasis mb-4">{{ descriptionText }}</div>

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

        <v-row>
          <v-col v-if="showFakeCard" cols="12" :md="isPaper || reviewMode ? 12 : 6">
            <v-card elevation="2" rounded="lg" class="h-100">
              <v-card-title class="d-flex justify-space-between align-center">
                <div class="d-flex align-center ga-2">
                  <v-icon color="error">mdi-alert-circle</v-icon>
                  <span class="text-h6">{{ fakeSectionTitle }}</span>
                  <v-chip color="error" size="small">{{ reviewMode ? fakeFiles.length : `${selectedFakeCount}/${fakeFiles.length}` }}</v-chip>
                </div>
                <v-btn v-if="!reviewMode" size="small" variant="text" color="error" @click="toggleSelect(fakeFiles)">
                  {{ isAllSelected(fakeFiles) ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text>
                <v-list v-if="fakeFiles.length" lines="two">
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
                  <v-chip color="success" size="small">{{ reviewMode ? effectiveNormalFiles.length : `${selectedNormalCount}/${effectiveNormalFiles.length}` }}</v-chip>
                </div>
                <v-btn v-if="!reviewMode" size="small" variant="text" color="success" @click="toggleSelect(effectiveNormalFiles)">
                  {{ isAllSelected(effectiveNormalFiles) ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text>
                <v-list v-if="effectiveNormalFiles.length" lines="two">
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
                当前 Review 检测结果为正常，无需发起人工审核。
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
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface ResourceFile {
  file_id: number
  file_name: string
  resource_type: string
  file_type: string
  file_size: number
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
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[] }): void
}>()

const selectedFileIds = ref<number[]>([])
const selectedReviewers = ref<number[]>([])

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
const reviewIsFake = computed(() => reviewMode.value && fakeFiles.value.length > 0)

const showFakeCard = computed(() => !reviewMode.value || reviewIsFake.value)
const showNormalCard = computed(() => !reviewMode.value || !reviewIsFake.value)

const detailTitle = computed(() => props.task.task_type === 'paper' ? '论文检测详情' : '同行评审 Review 检测详情')

const totalCountLabel = computed(() => props.task.task_type === 'paper' ? '论文总数' : 'Review 总数')
const fakeCountLabel = computed(() => props.task.task_type === 'paper' ? '造假论文数量' : '造假 Review 数量')
const fakeSectionTitle = computed(() => props.task.task_type === 'paper' ? '疑似造假论文' : '疑似造假 Review')
const normalSectionTitle = computed(() => props.task.task_type === 'paper' ? '正常论文' : '正常 Review')
const emptyFakeText = computed(() => props.task.task_type === 'paper' ? '暂无疑似造假论文' : '暂无疑似造假 Review')
const emptyNormalText = computed(() => props.task.task_type === 'paper' ? '暂无正常论文' : '暂无正常 Review')

const defaultSummary = computed(() => props.task.task_type === 'paper' ? '论文检测任务已创建，等待系统输出完整结论。' : 'Review 检测任务已创建，等待系统输出完整结论。')

const descriptionText = computed(() => {
  if (props.task.task_type === 'paper') {
    return '展示论文 AIGC 概率、可疑段落分析及参考文献分析相关结果，支持下载综合鉴伪报告并发起人工复核。'
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

const totalCount = computed(() => fakeFiles.value.length + effectiveNormalFiles.value.length)
const fakeCount = computed(() => fakeFiles.value.length)
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
    return selectedReviewers.value.length > 0 && fakeFiles.value.length > 0
  }
  return selectedReviewers.value.length > 0 && selectedFileIds.value.length > 0
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
    : selectedFileIds.value

  emit('request-review', {
    reviewers: selectedReviewers.value,
    selected_file_ids: selectedIds,
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
</script>
