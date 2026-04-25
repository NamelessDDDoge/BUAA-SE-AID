<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">人工审核管理</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">
          查看出版社提交的人工审核申请，并对图像、论文和 Review 审核请求进行审批。
        </div>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="searchQuery"
          label="搜索发布者"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          variant="outlined"
          hide-details
          @keyup.enter="fetchRequests"
        />
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12">
        <TaskTypeFilter v-model="taskTypeFilter" :options="taskTypeOptions" />
      </v-col>
    </v-row>

    <v-card elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center">
        <span class="text-h6">审核请求</span>
        <v-spacer />
        <span class="text-caption text-medium-emphasis">共 {{ totalRequests }} 条</span>
      </v-card-title>
      <v-data-table :headers="headers" :items="requests" :loading="loadingRequests" hide-default-footer>
        <template #item.task_type="{ item }">
          <v-chip size="small" variant="tonal" :color="item.task_type === 'paper' ? 'deep-orange' : item.task_type === 'review' ? 'teal' : 'primary'">
            {{ getTaskTypeName(item.task_type) }}
          </v-chip>
        </template>
        <template #item.state="{ item }">
          <v-chip size="small" :color="getStateColor(item.state)">{{ getStateName(item.state) }}</v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-eye" variant="text" color="primary" @click="openReviewDialog(item)" />
        </template>
      </v-data-table>
      <div class="d-flex align-center justify-center pa-4">
        <div class="d-flex align-center">
          <span class="text-caption mr-2">每页显示</span>
          <v-select
            v-model="pageSize"
            :items="[5, 10, 20, 50, 100]"
            density="compact"
            variant="outlined"
            hide-details
            style="width: 100px"
            @update:model-value="handlePageSizeChange"
          />
        </div>
        <v-pagination v-model="currentPage" :length="totalPages" :total-visible="7" class="ml-4" @update:model-value="handlePageChange" />
      </div>
    </v-card>

    <v-dialog v-model="showReviewDialog" max-width="800">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">审核请求详情</v-card-title>
        <v-card-text>
          <div v-if="selectedRequest" class="d-flex flex-column ga-4">
            <div class="d-flex align-center">
              <v-avatar size="40" class="mr-4">
                <v-img :src="selectedRequest.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'" :alt="selectedRequest.username" />
              </v-avatar>
              <div>
                <div class="text-h6">{{ selectedRequest.username }}</div>
                <div class="text-caption text-medium-emphasis">{{ selectedRequest.time }}</div>
              </div>
            </div>

            <v-chip :color="getStateColor(selectedRequest.state)" size="small">{{ getStateName(selectedRequest.state) }}</v-chip>

            <div v-if="reviewDetails" class="d-flex flex-column ga-4">
              <div v-if="reviewDetails.reason">
                <div class="text-subtitle-1 font-weight-bold mb-2">申请理由</div>
                <div class="text-body-1">{{ reviewDetails.reason }}</div>
              </div>

              <div v-if="reviewDetails.selected_files?.length">
                <div class="text-subtitle-1 font-weight-bold mb-2">已选文件</div>
                <v-list density="compact">
                  <v-list-item v-for="file in reviewDetails.selected_files" :key="file.id || file.file_id">
                    <v-list-item-title>{{ file.file_name }}</v-list-item-title>
                    <v-list-item-subtitle>{{ file.resource_type }} · {{ file.file_type }}</v-list-item-subtitle>
                    <template #append>
                      <div class="d-flex ga-2">
                        <v-btn size="small" variant="text" prepend-icon="mdi-eye-outline" @click="previewFile(file)">预览</v-btn>
                        <v-btn size="small" variant="text" prepend-icon="mdi-download" :disabled="!file.file_url" @click="downloadFile(file)">下载</v-btn>
                      </div>
                    </template>
                  </v-list-item>
                </v-list>
              </div>

              <div v-if="reviewDetails.imgs?.length">
                <div class="text-subtitle-1 font-weight-bold mb-2">图像</div>
                <v-row>
                  <v-col v-for="img in reviewDetails.imgs" :key="img.id" cols="4">
                    <v-img :src="getImageUrl(img.url)" height="80" cover class="rounded" />
                  </v-col>
                </v-row>
              </div>

              <div>
                <div class="text-subtitle-1 font-weight-bold mb-2">指定审核员</div>
                <div class="d-flex flex-wrap ga-4">
                  <div v-for="person in reviewDetails.persons" :key="person.id" class="d-flex align-center">
                    <v-avatar size="32" class="mr-2">
                      <v-img :src="getImageUrl(person.avatar)" :alt="person.username" />
                    </v-avatar>
                    <span>{{ person.username }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="error" variant="text" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(0)">拒绝</v-btn>
          <v-btn color="success" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(1)">通过</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import reviewApi from '@/api/review'
import TaskTypeFilter from '@/features/tasks/TaskTypeFilter.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

interface ReviewRequest {
  id: number
  request_type: 'image' | 'resource'
  task_type: 'image' | 'paper' | 'review'
  task_id?: number | null
  task_name?: string | null
  username: string
  avatar: string
  state: string
  time: string
}

const headers = [
  { title: '发布者', key: 'username', align: 'start' as const },
  { title: '任务类型', key: 'task_type', align: 'center' as const },
  { title: '状态', key: 'state', align: 'center' as const },
  { title: '提交时间', key: 'time', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false },
]

type ReviewTaskType = '' | 'image' | 'paper' | 'review'

const taskTypeFilter = ref<ReviewTaskType>('')
const taskTypeOptions = [
  { label: '全部', value: '', color: 'primary' },
  { label: '图像', value: 'image', color: 'primary' },
  { label: 'Review', value: 'review', color: 'teal' },
  { label: '论文', value: 'paper', color: 'deep-orange' },
]

const requests = ref<ReviewRequest[]>([])
const loadingRequests = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalRequests = ref(0)
const totalPages = ref(1)
const searchQuery = ref('')
const showReviewDialog = ref(false)
const selectedRequest = ref<ReviewRequest | null>(null)
const reviewDetails = ref<any>(null)
const rejectReason = ref('')
const previewDialog = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('')
const previewText = ref('')
const previewError = ref('')

const getImageUrl = (url: string) => import.meta.env.VITE_API_URL + url

const getTaskTypeName = (taskType: string) => ({
  image: '图像',
  paper: '论文',
  review: 'Review',
}[taskType] || taskType)

const getFileUrl = (file: any) => {
  if (!file?.file_url) return ''
  if (/^https?:\/\//.test(file.file_url)) return file.file_url
  return `${import.meta.env.VITE_API_URL || ''}${file.file_url}`
}

const downloadFile = (file: any) => {
  const url = getFileUrl(file)
  if (!url) return
  const link = document.createElement('a')
  link.href = url
  link.download = file.file_name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const previewFile = async (file: any) => {
  previewDialog.value = true
  previewLoading.value = true
  previewTitle.value = file.file_name
  previewText.value = ''
  previewError.value = ''
  try {
    const response = await reviewApi.getResourceTextPreview(file.file_id || file.id)
    previewText.value = response.data?.text_content || '暂无可预览文本。'
    if (response.data?.text_truncated) {
      previewError.value = '文件较长，当前仅展示前 60000 字。'
    }
  } catch (error: any) {
    previewError.value = error?.response?.data?.message || '当前文件暂不支持预览，请下载查看。'
  } finally {
    previewLoading.value = false
  }
}

const getStateColor = (state: string) => ({
  pending: 'warning',
  refused: 'error',
  accepted: 'success',
}[state] || 'grey')

const getStateName = (state: string) => ({
  pending: '待审核',
  refused: '已拒绝',
  accepted: '已通过',
  pending: '待审核',
  refused: '已拒绝',
  accepted: '已通过',
}[state] || state)

const fetchRequests = async () => {
  loadingRequests.value = true
  try {
    const response = await reviewApi.getReviewRequests({
      page: currentPage.value,
      page_size: pageSize.value,
      query: searchQuery.value || '',
      task_type: taskTypeFilter.value || '',
    })
    const { requests: requestList, current_page, total_pages, total_requests } = response.data
    requests.value = requestList.map((request: any) => ({
      id: request.id,
      request_type: request.request_type || 'image',
      task_type: request.task_type || 'image',
      task_id: request.task_id,
      task_name: request.task_name,
      username: request.username,
      avatar: request.avatar ? import.meta.env.VITE_API_URL + request.avatar : '',
      state: request.state,
      time: request.time,
    }))
    currentPage.value = current_page
    totalPages.value = total_pages
    totalRequests.value = total_requests
  } catch (error) {
    console.error('Failed to fetch review requests:', error)
    snackbar.showMessage('获取审核请求失败。', 'error')
  } finally {
    loadingRequests.value = false
  }
}

const openReviewDialog = async (request: ReviewRequest) => {
  selectedRequest.value = request
  try {
    const response = await reviewApi.getReviewRequestDetails(request.id, request.request_type)
    reviewDetails.value = response.data
    showReviewDialog.value = true
  } catch (error) {
    console.error('Failed to fetch review request detail:', error)
    snackbar.showMessage('获取审核请求详情失败。', 'error')
  }
}

const handleReviewRequest = async (choice: number) => {
  if (!selectedRequest.value) return
  try {
    await reviewApi.handleReviewRequest(selectedRequest.value.id, {
      choice,
      reason: rejectReason.value,
      request_type: selectedRequest.value.request_type,
    })
    snackbar.showMessage(choice === 1 ? '审核请求已通过。' : '审核请求已拒绝。', 'success')
    showReviewDialog.value = false
    rejectReason.value = ''
    await fetchRequests()
  } catch (error) {
    console.error('Failed to handle review request:', error)
    snackbar.showMessage('处理审核请求失败。', 'error')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchRequests()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchRequests()
}

watch(taskTypeFilter, async () => {
  await fetchRequests()
})

onMounted(async () => {
  await fetchRequests()
})
</script>

<style scoped>
.page-shell {
  max-width: 1400px;
}

.file-preview {
  max-height: 60vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
</style>
