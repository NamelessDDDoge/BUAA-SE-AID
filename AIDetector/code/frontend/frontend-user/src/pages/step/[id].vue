<template>
  <v-card flat border="0">
    <v-card-text class="pa-0 mt-4">
      <div v-if="loading" class="d-flex justify-center py-16">
        <v-progress-circular indeterminate color="primary" />
      </div>

      <DetectionReviewStep
        v-else-if="taskDetail?.task_type === 'image'"
        :task_id="taskId"
      />

      <ResourceDetectionDetailStep
        v-else-if="taskDetail && (taskDetail.task_type === 'paper' || taskDetail.task_type === 'review')"
        :task="taskDetail"
        :reviewer-options="reviewerOptions"
        @download="downloadTaskReport"
        @request-review="handleResourceReviewRequest"
      />

      <v-alert v-else type="warning" variant="tonal" class="ma-4">
        未获取到任务详情，请返回检测历史重试。
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
//注意鉴权！！！
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteParams } from 'vue-router'
import DetectionReviewStep from '@/components/steps/DetectionReviewStep.vue'
import ResourceDetectionDetailStep from '@/components/steps/ResourceDetectionDetailStep.vue'
import { useSnackbarStore } from '@/stores/snackbar';
import publisher from '@/api/publisher'
import { useUserStore } from '@/stores/user'
const snackbar = useSnackbarStore();
const userStore = useUserStore()

const router = useRouter()
const route = useRoute()

// 获取任务ID
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
    const response = await publisher.downloadReport(taskId.value)
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
    snackbar.showMessage('报告下载成功', 'success')
  } catch {
    snackbar.showMessage('报告下载失败', 'error')
  }
}

const handleResourceReviewRequest = async (payload: { reviewers: number[]; selected_file_ids: number[] }) => {
  try {
    const resp = await publisher.submitResourceReviewRequest({
      task_id: taskId.value,
      reviewers: payload.reviewers,
      selected_file_ids: payload.selected_file_ids,
    })
    if (resp?.data?.placeholder) {
      snackbar.showMessage('人工审核请求已提交（占位接口），后续将接入正式流程', 'success')
      return
    }
    snackbar.showMessage('人工审核请求已提交', 'success')
  } catch (error: any) {
    const message = error?.response?.data?.error || '人工审核请求提交失败'
    snackbar.showMessage(message, 'error')
  }
}

// 组件挂载时获取任务数据
onMounted(async () => {
  loading.value = true
  try {
    const response = (await publisher.ifHasPermission({ task_id: taskId.value })).data.access
    if (response !== true) {
      router.push('/404')
      return
    }

    const taskResp = await publisher.getDetectionTaskDetail({ task_id: taskId.value })
    taskDetail.value = taskResp.data

    if (taskDetail.value?.task_type === 'paper' || taskDetail.value?.task_type === 'review') {
      const reviewersResp = await publisher.getReviewers({ publisher_id: userStore.id })
      reviewerOptions.value = Array.isArray(reviewersResp.data?.reviewers) ? reviewersResp.data.reviewers : []
    }
  } catch {
    snackbar.showMessage('任务详情获取失败', 'error')
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
