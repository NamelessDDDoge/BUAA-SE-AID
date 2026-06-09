<template>
  <v-card flat border="0">
    <v-card-text class="pa-0 mt-4">
      <!-- Loading state -->
      <div v-if="loading" class="d-flex justify-center py-16">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <!-- Progress panel when task is running (pending / in_progress) -->
      <div v-else-if="isRunning" class="d-flex flex-column align-center py-12 px-6">
        <v-card class="pa-8 text-center" max-width="520" flat border>
          <v-icon size="64" color="primary" class="mb-4">mdi-file-document-search-outline</v-icon>
          <h2 class="text-h5 font-weight-bold mb-2">检测进行中</h2>
          <p class="text-body-1 text-medium-emphasis mb-6">{{ taskProgressLabel }}</p>

          <div class="d-flex align-center ga-4 mb-2">
            <v-progress-linear
              :model-value="taskProgress"
              height="12"
              color="primary"
              rounded
              class="flex-grow-1"
            />
            <span class="text-h6 font-weight-bold" style="min-width: 48px">{{ taskProgress }}%</span>
          </div>

          <div class="text-caption text-medium-emphasis mt-3">
            <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
            页面将自动刷新检测进度
          </div>

          <v-divider class="my-6" />

          <div class="d-flex justify-center ga-3">
            <v-btn variant="outlined" color="grey" @click="router.back()">
              返回
            </v-btn>
            <v-btn
              variant="tonal"
              color="primary"
              :loading="refreshing"
              @click="manualRefresh"
            >
              刷新状态
            </v-btn>
          </div>
        </v-card>
      </div>

      <!-- Completed task results -->
      <DetectionReviewStep v-else-if="taskDetail?.task_type === 'image'" :task_id="taskId" />

      <PaperResultView
        v-else-if="taskDetail?.task_type === 'paper'"
        :task="taskDetail"
        :reviewer-options="reviewerOptions"
        @download="downloadTaskReport"
        @request-review="handleResourceReviewRequest"
      />

      <ReviewResultView
        v-else-if="taskDetail?.task_type === 'review'"
        :task="taskDetail"
        :reviewer-options="reviewerOptions"
        @download="downloadTaskReport"
        @request-review="handleResourceReviewRequest"
      />

      <v-alert v-else type="warning" variant="tonal" class="ma-4">
        The task detail payload could not be loaded. Return to history and retry.
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteParams } from 'vue-router'
import DetectionReviewStep from '@/components/steps/DetectionReviewStep.vue'
import PaperResultView from '@/features/results/PaperResultView.vue'
import ReviewResultView from '@/features/results/ReviewResultView.vue'
import { useSnackbarStore } from '@/stores/snackbar'
import detectionApi from '@/api/detection'
import resourceTasksApi from '@/api/resourceTasks'
import reviewTasksApi from '@/api/reviewTasks'
import publisher from '@/api/publisher'
import { useUserStore } from '@/stores/user'

const snackbar = useSnackbarStore()
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const taskId = computed(() => (route.params as RouteParams & { id: string }).id)
const loading = ref(false)
const refreshing = ref(false)
const reviewerOptions = ref<Array<{ id: number; username: string; avatar?: string | null }>>([])
let pollTimer: number | null = null
const POLL_INTERVAL = 3000

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
  progress_percentage?: number
  progress_step?: string
  progress_step_label?: string
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

const taskDetail = ref<TaskDetail | null>(null)

const isRunning = computed(() =>
  taskDetail.value && ['pending', 'in_progress'].includes(taskDetail.value.status),
)

const taskProgress = computed(() => taskDetail.value?.progress_percentage || 0)

const taskProgressLabel = computed(() => {
  const stepLabel = taskDetail.value?.progress_step_label
  if (stepLabel) return stepLabel
  if (taskDetail.value?.status === 'pending') return '排队等待中 ...'
  return '正在进行检测 ...'
})

const downloadTaskReport = async () => {
  try {
    const response = await detectionApi.downloadTaskReport(taskId.value)
    const contentDisposition = response.headers['content-disposition']

    let fileName = `task_${taskId.value}_report.pdf`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/)
      if (match) fileName = match[1]
    }

    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    snackbar.showMessage('Report downloaded successfully.', 'success')
  } catch {
    snackbar.showMessage('Failed to download the report.', 'error')
  }
}

const handleResourceReviewRequest = async (payload: { reviewers: number[]; selected_file_ids: number[]; reason: string }) => {
  try {
    const resp = await resourceTasksApi.submitReviewRequest({
      task_id: taskId.value,
      reviewers: payload.reviewers,
      selected_file_ids: payload.selected_file_ids,
      reason: payload.reason,
    })
    if (resp?.data?.placeholder) {
      snackbar.showMessage('The placeholder review-request API accepted the submission.', 'success')
      return
    }
    snackbar.showMessage('Review request submitted.', 'success')
  } catch (error: any) {
    const message = error?.response?.data?.error || 'Failed to submit the review request.'
    snackbar.showMessage(message, 'error')
  }
}

const fetchTaskStatus = async () => {
  try {
    const taskResp = await detectionApi.getTaskDetail(taskId.value)
    taskDetail.value = taskResp.data
    return taskResp.data?.status as string
  } catch {
    return 'error'
  }
}

const manualRefresh = async () => {
  refreshing.value = true
  try {
    const status = await fetchTaskStatus()
    if (status === 'completed' || status === 'failed') {
      stopPolling()
      await loadReviewerOptions()
    }
  } finally {
    refreshing.value = false
  }
}

const startPolling = () => {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    const status = await fetchTaskStatus()
    if (status === 'completed' || status === 'failed') {
      stopPolling()
      await loadReviewerOptions()
      snackbar.showMessage(
        status === 'completed' ? '检测已完成。' : '检测失败。',
        status === 'completed' ? 'success' : 'error',
      )
    }
  }, POLL_INTERVAL)
}

const stopPolling = () => {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

const loadReviewerOptions = async () => {
  if (taskDetail.value?.task_type === 'paper' || taskDetail.value?.task_type === 'review') {
    try {
      const reviewersResp = await reviewTasksApi.getReviewers({ publisher_id: userStore.id })
      reviewerOptions.value = Array.isArray(reviewersResp.data?.reviewers) ? reviewersResp.data.reviewers : []
    } catch {
      reviewerOptions.value = []
    }
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const response = (await publisher.ifHasPermission({ task_id: taskId.value })).data.access
    if (response !== true) {
      router.push('/404')
      return
    }

    const status = await fetchTaskStatus()

    if (['pending', 'in_progress'].includes(status)) {
      startPolling()
      loading.value = false
      return
    }

    if (taskDetail.value?.task_type === 'paper' || taskDetail.value?.task_type === 'review') {
      await loadReviewerOptions()
    }
  } catch {
    snackbar.showMessage('Failed to fetch the task detail.', 'error')
    router.push('/history')
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
.v-card {
  box-shadow: none;
}
</style>
