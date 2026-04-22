<template>
  <v-card flat border="0">
    <v-card-text class="pa-0 mt-4">
      <div v-if="loading" class="d-flex justify-center py-16">
        <v-progress-circular indeterminate color="primary" />
      </div>

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
import { computed, onMounted, ref } from 'vue'
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
const reviewerOptions = ref<Array<{ id: number; username: string; avatar?: string | null }>>([])

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

const taskDetail = ref<TaskDetail | null>(null)

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

const handleResourceReviewRequest = async (payload: { reviewers: number[]; selected_file_ids: number[] }) => {
  try {
    const resp = await resourceTasksApi.submitReviewRequest({
      task_id: taskId.value,
      reviewers: payload.reviewers,
      selected_file_ids: payload.selected_file_ids,
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

onMounted(async () => {
  loading.value = true
  try {
    const response = (await publisher.ifHasPermission({ task_id: taskId.value })).data.access
    if (response !== true) {
      router.push('/404')
      return
    }

    const taskResp = await detectionApi.getTaskDetail(taskId.value)
    taskDetail.value = taskResp.data

    if (taskDetail.value?.task_type === 'paper' || taskDetail.value?.task_type === 'review') {
      const reviewersResp = await reviewTasksApi.getReviewers({ publisher_id: userStore.id })
      reviewerOptions.value = Array.isArray(reviewersResp.data?.reviewers) ? reviewersResp.data.reviewers : []
    }
  } catch {
    snackbar.showMessage('Failed to fetch the task detail.', 'error')
    router.push('/history')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.v-card {
  box-shadow: none;
}
</style>
