<template>
  <v-card flat border="0">
    <v-card-title class="d-flex flex-wrap align-center pa-0 ga-3">
      <div>
        <h1 class="text-h4 font-weight-bold">检测历史</h1>
        <div class="text-caption text-medium-emphasis mt-1">默认按时间倒序显示最近半年的任务</div>
      </div>
      <v-spacer />
      <v-text-field
        v-model="filters.keyword"
        density="comfortable"
        variant="outlined"
        prepend-inner-icon="mdi-magnify"
        placeholder="搜索任务名称、关键词或任务编号"
        clearable
        hide-details
        class="search-input"
      />
      <v-btn variant="outlined" :color="hasActiveFilters ? 'primary' : undefined" @click="showFilter = true">
        <v-icon class="mr-2">mdi-filter</v-icon>
        筛选
      </v-btn>
      <v-btn
        color="error"
        variant="outlined"
        prepend-icon="mdi-delete-sweep"
        :disabled="!tasks.length"
        @click="showClearDialog = true"
      >
        清空历史
      </v-btn>
    </v-card-title>

    <v-card-text class="pa-0 mt-4">
      <v-data-table
        :headers="headers"
        :items="tasks"
        :loading="loading"
        :items-per-page="pageSize"
        class="elevation-1"
        item-value="task_id"
        hide-default-footer
      >
        <template #item.task_id="{ item }">
          <v-btn variant="text" color="primary" @click="openTaskDetail(item)">#{{ item.task_id }}</v-btn>
        </template>

        <template #item.task_type="{ item }">
          <v-chip size="small" color="indigo-lighten-4" class="text-indigo-darken-4">
            {{ getTaskTypeLabel(item.task_type) }}
          </v-chip>
        </template>

        <template #item.upload_time="{ item }">
          <span>{{ formatDateTime(item.upload_time) }}</span>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small">
            {{ getStatus(item.status) }}
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex justify-center ga-2">
            <v-btn size="small" color="primary" variant="text" :disabled="item.status !== 'completed'" @click="goToTaskPage(item)">
              下一步
            </v-btn>
            <v-btn
              size="small"
              color="secondary"
              variant="text"
              :disabled="item.status !== 'completed'"
              @click="downloadTaskReport(item)"
            >
              下载报告
            </v-btn>
            <v-btn size="small" color="error" variant="text" :disabled="item.status === 'in_progress'" @click="openDeleteDialog(item)">
              删除
            </v-btn>
          </div>
        </template>

        <template #top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">共 {{ totalTasks }} 条记录</div>
          </div>
        </template>

        <template #no-data>
          <div class="py-8 text-center text-medium-emphasis">暂无符合条件的检测记录</div>
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
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          class="ml-4"
          @update:model-value="handlePageChange"
        />
      </div>
    </v-card-text>

    <v-dialog v-model="showFilter" max-width="520">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column ga-4">
            <v-select v-model="filters.status" :items="statusOptions" label="任务状态" clearable hide-details />
            <v-select v-model="filters.taskType" :items="taskTypeOptions" label="任务类别" clearable hide-details />
            <v-select
              v-model="filters.timeRange"
              :items="timeRangeOptions"
              label="快速选择时间范围"
              clearable
              hide-details
              @update:model-value="handleTimeRangeChange"
            />
            <div class="d-flex align-center ga-3">
              <v-text-field
                v-model="filters.startDate"
                label="开始时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              />
              <v-text-field
                v-model="filters.endDate"
                label="结束时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              />
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showDetail" max-width="640">
      <v-card v-if="currentTask">
        <v-card-title class="d-flex align-center">
          任务详情
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="showDetail = false" />
        </v-card-title>
        <v-card-text class="pt-2">
          <v-list lines="two">
            <v-list-item title="任务编号" :subtitle="String(currentTask.task_id)" />
            <v-list-item title="任务名称" :subtitle="currentTask.task_name || '-'" />
            <v-list-item title="检测对象类型" :subtitle="getTaskTypeLabel(currentTask.task_type)" />
            <v-list-item title="提交时间" :subtitle="formatDateTime(currentTask.upload_time)" />
            <v-list-item title="完成时间" :subtitle="formatDateTime(currentTask.completion_time) || '-'" />
            <v-list-item title="检测状态" :subtitle="getStatus(currentTask.status)" />
            <v-list-item title="结果摘要" :subtitle="currentTask.result_summary || '-'" />
            <v-list-item v-if="currentTask.error_message" title="错误信息" :subtitle="currentTask.error_message" />
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="text" :disabled="currentTask.status !== 'completed'" @click="goToTaskPage(currentTask)">
            下一步
          </v-btn>
          <v-btn
            color="secondary"
            variant="text"
            :disabled="currentTask.status !== 'completed'"
            @click="downloadTaskReport(currentTask)"
          >
            下载报告
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showDeleteDialog" max-width="420">
      <v-card>
        <v-card-title class="text-h6">删除确认</v-card-title>
        <v-card-text>确认删除任务 #{{ pendingDeleteTask?.task_id }} 吗？删除后无法恢复。</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="confirmDelete">确认删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showClearDialog" max-width="460">
      <v-card>
        <v-card-title class="text-h6">清空历史确认</v-card-title>
        <v-card-text>
          将删除当前账号下的全部检测任务、上传文件与关联结果。这个操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showClearDialog = false">取消</v-btn>
          <v-btn color="error" :loading="clearing" @click="confirmClearHistory">确认清空</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import publisher from '@/api/publisher'

interface Task {
  task_id: number
  task_type: 'image' | 'paper' | 'review'
  task_name: string
  upload_time: string
  completion_time: string | null
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  result_summary: string
  error_message?: string | null
}

const router = useRouter()
const snackbar = useSnackbarStore()

const pageSize = ref(10)
const currentPage = ref(1)
const totalTasks = ref(0)
const totalPages = ref(1)
const loading = ref(false)
const deleting = ref(false)
const clearing = ref(false)
let searchTimer: number | null = null

const headers = [
  { title: '任务 ID', key: 'task_id', align: 'center' as const, width: '120px' },
  { title: '任务名称', key: 'task_name', align: 'center' as const, width: '180px' },
  { title: '对象类型', key: 'task_type', align: 'center' as const, width: '120px' },
  { title: '上传时间', key: 'upload_time', align: 'center' as const, width: '180px' },
  { title: '检测状态', key: 'status', align: 'center' as const, width: '120px' },
  { title: '结果摘要', key: 'result_summary', align: 'center' as const, width: '180px' },
  { title: '操作', key: 'actions', sortable: false, align: 'center' as const, width: '280px' },
]

const tasks = ref<Task[]>([])
const showFilter = ref(false)
const showDetail = ref(false)
const currentTask = ref<Task | null>(null)
const showDeleteDialog = ref(false)
const pendingDeleteTask = ref<Task | null>(null)
const showClearDialog = ref(false)
const timeError = ref('')

const filters = ref<{
  status: string | null
  taskType: 'image' | 'paper' | 'review' | null
  timeRange: string | null
  startDate: string | null
  endDate: string | null
  keyword: string
}>({
  status: null,
  taskType: null,
  timeRange: null,
  startDate: null,
  endDate: null,
  keyword: '',
})

const statusOptions = [
  { title: '排队中', value: 'pending' },
  { title: '进行中', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
  { title: '失败', value: 'failed' },
] as const

const taskTypeOptions = [
  { title: '学术图像检测', value: 'image' },
  { title: '全文论文检测', value: 'paper' },
  { title: '同行评审 Review 检测', value: 'review' },
] as const

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近半年', value: '183d' },
  { title: '最近一年', value: '365d' },
] as const

const formatDateFilter = (timestamp: number) => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
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

const hasActiveFilters = computed(() => {
  return Boolean(
    filters.value.keyword.trim() ||
    filters.value.startDate ||
    filters.value.endDate ||
    filters.value.status !== null ||
    filters.value.taskType !== null ||
    filters.value.timeRange !== null,
  )
})

const fetchTasks = async (page: number, size: number) => {
  loading.value = true
  try {
    const params: any = { page, page_size: size }

    if (filters.value.status) params.status = filters.value.status
    if (filters.value.taskType) params.task_type = filters.value.taskType
    if (filters.value.keyword.trim()) params.keyword = filters.value.keyword.trim()

    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '183d': 183 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000,
      }
      const rangeMs = ranges[filters.value.timeRange]
      params.startTime = formatDateFilter(now - rangeMs)
      params.endTime = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      params.startTime = formatDateFilter(new Date(filters.value.startDate).getTime())
      params.endTime = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const response = await publisher.getAllDetectionTask(params)
    const { tasks: taskList, current_page, total_pages, total_tasks } = response.data
    tasks.value = taskList.map((task: any) => ({
      task_id: task.task_id,
      task_type: task.task_type || 'image',
      task_name: task.task_name || `任务 ${task.task_id}`,
      upload_time: task.upload_time,
      completion_time: task.completion_time,
      status: task.status,
      result_summary: task.result_summary || '-',
      error_message: task.error_message || null,
    }))
    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = total_tasks
  } catch (error) {
    console.error('获取任务列表失败:', error)
    snackbar.showMessage('获取任务列表失败', 'error')
  } finally {
    loading.value = false
  }
}

const handleTimeRangeChange = (value: string | null) => {
  if (value) {
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

const handleCustomTimeChange = () => {
  filters.value.timeRange = null
  if ((!filters.value.startDate && filters.value.endDate) || (filters.value.startDate && !filters.value.endDate)) {
    timeError.value = '开始时间和结束时间必须同时设置或同时为空'
    return
  }
  if (!filters.value.startDate && !filters.value.endDate) {
    timeError.value = ''
    return
  }
  const start = new Date(filters.value.startDate!).getTime()
  const end = new Date(filters.value.endDate!).getTime()
  timeError.value = start >= end ? '开始时间必须早于结束时间' : ''
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchTasks(page, pageSize.value)
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks(1, size)
}

const getStatus = (status: string) => {
  switch (status) {
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
}

const getTaskTypeLabel = (taskType: string) => {
  switch (taskType) {
    case 'image':
      return '图像'
    case 'paper':
      return '论文'
    case 'review':
      return 'Review'
    default:
      return '未知'
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
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
}

const resetFilters = () => {
  filters.value = {
    status: null,
    taskType: null,
    timeRange: null,
    startDate: null,
    endDate: null,
    keyword: '',
  }
  timeError.value = ''
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

const applyFilters = () => {
  if (timeError.value) return
  showFilter.value = false
  currentPage.value = 1
  fetchTasks(1, pageSize.value)
}

const openTaskDetail = (item: Task) => {
  currentTask.value = item
  showDetail.value = true
}

const goToTaskPage = (item: Task) => {
  router.push(`/step/${item.task_id}`)
}

const downloadTaskReport = async (item: Task) => {
  try {
    const response = await publisher.downloadReport(item.task_id)
    const contentDisposition = response.headers['content-disposition']
    let fileName = `task_${item.task_id}_report.pdf`
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
  } catch (error: any) {
    if (error?.response?.status === 202) {
      snackbar.showMessage('报告正在生成中，请稍后重试', 'warning')
      return
    }
    snackbar.showMessage('报告下载失败', 'error')
  }
}

const openDeleteDialog = (item: Task) => {
  pendingDeleteTask.value = item
  showDeleteDialog.value = true
}

const confirmDelete = async () => {
  if (!pendingDeleteTask.value) return
  deleting.value = true
  try {
    await publisher.deleteDetectionTask({ task_id: pendingDeleteTask.value.task_id })
    showDeleteDialog.value = false
    pendingDeleteTask.value = null
    snackbar.showMessage('删除成功', 'success')
    await fetchTasks(currentPage.value, pageSize.value)
  } catch {
    snackbar.showMessage('删除检测任务失败', 'error')
  } finally {
    deleting.value = false
  }
}

const confirmClearHistory = async () => {
  clearing.value = true
  try {
    await publisher.clearDetectionHistory()
    showClearDialog.value = false
    currentTask.value = null
    pendingDeleteTask.value = null
    snackbar.showMessage('历史已清空', 'success')
    await fetchTasks(1, pageSize.value)
  } catch {
    snackbar.showMessage('清空历史失败', 'error')
  } finally {
    clearing.value = false
  }
}

onMounted(() => {
  fetchTasks(currentPage.value, pageSize.value)
})

watch(() => filters.value.keyword, () => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    currentPage.value = 1
    fetchTasks(1, pageSize.value)
  }, 300)
})

onBeforeUnmount(() => {
  if (searchTimer) window.clearTimeout(searchTimer)
})
</script>

<style scoped>
.v-data-table {
  width: 100%;
}

.search-input {
  min-width: 320px;
  max-width: 420px;
}
</style>
