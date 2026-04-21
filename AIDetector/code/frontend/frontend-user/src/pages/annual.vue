<template>
  <div class="annual-page">
    <!-- 标题 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">我的任务</h1>
      </v-col>
    </v-row>

    <!-- 筛选按钮 -->
    <v-row class="mb-4">
      <v-col cols="12" class="d-flex justify-end">
        <v-btn 
          color="primary" 
          class="text-none" 
          prepend-icon="mdi-filter-variant"
          @click="showFilterDialog = true"
        >
          筛选
        </v-btn>
      </v-col>
    </v-row>

    <v-card class="elevation-2">
      <v-data-table
        :headers="headers"
        :items="tasks"
        class="elevation-0"
        :items-per-page="pageSize"
        hover
        :width="'100%'"
        :loading="loading"
        hide-default-footer
      >
        <template v-slot:top>
          <div class="d-flex align-center pa-4">
            <div class="text-caption text-medium-emphasis">
              共 {{ totalTasks }} 条记录
            </div>
          </div>
        </template>

        <template v-slot:item.status="{ item }">
          <v-chip
            :color="getStatusColor(item.status)"
            size="small"
            class="status-chip"
          >
            {{ getStatusName(item.status) }}
          </v-chip>
        </template>

        <template v-slot:item.progress="{ item }">
          <div class="d-flex align-center">
            <v-progress-linear
              :model-value="getProgressValue(item.progress)"
              :color="getProgressColor(item.progress)"
              height="20"
            >
              <template v-slot:default="{ value }">
                <span class="text-caption">{{ item.progress }}</span>
              </template>
            </v-progress-linear>
          </div>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon
            variant="text"
            size="small"
            color="primary"
            class="mr-2"
            @click="goToTaskDetail(item)"
          >
            <v-icon>mdi-eye</v-icon>
          </v-btn>
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
          ></v-select>
          <span class="text-caption ml-2">条</span>
        </div>
        <v-pagination
          v-model="currentPage"
          :length="totalPages"
          :total-visible="7"
          class="ml-4"
          @update:model-value="handlePageChange"
        ></v-pagination>
      </div>
    </v-card>

    <!-- 筛选对话框 -->
    <v-dialog v-model="showFilterDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">筛选条件</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column gap-4">
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="任务状态"
              clearable
              hide-details
            ></v-select>
            
            <v-select
              v-model="filters.timeRange"
              :items="timeRangeOptions"
              label="快速选择时间范围"
              clearable
              hide-details
              @update:model-value="handleTimeRangeChange"
            ></v-select>

            <div class="d-flex align-center gap-4">
              <v-text-field
                v-model="filters.startDate"
                label="开始时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              ></v-text-field>
              <v-text-field
                v-model="filters.endDate"
                label="结束时间"
                type="datetime-local"
                hide-details
                density="compact"
                :error-messages="timeError"
                @update:model-value="handleCustomTimeChange"
              ></v-text-field>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="resetFilters">重置</v-btn>
          <v-btn color="primary" @click="applyFilters">应用</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import publisherApi from '@/api/publisher'
import { useSnackbarStore } from '@/stores/snackbar'

const router = useRouter()
const snackbar = useSnackbarStore()

interface Task {
  review_request_id: number
  request_time: string
  status: string
  progress: string
}

const headers = [
  { title: '任务ID', key: 'review_request_id', align: 'start' },
  { title: '提交时间', key: 'request_time', align: 'center' },
  { title: '状态', key: 'status', align: 'center' },
  { title: '进度', key: 'progress', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false },
] as const

// 分页相关
const tasks = ref<Task[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)
const totalPages = ref(1)

// 筛选相关
const showFilterDialog = ref(false)
const filters = ref<{
  status: string | null
  timeRange: string | null
  startDate: string | null
  endDate: string | null
}>({
  status: null,
  timeRange: null,
  startDate: null,
  endDate: null
})

const statusOptions = [
  { title: '审核中', value: 'pending' },
  { title: '已下发', value: 'in_progress' },
  { title: '已完成', value: 'completed' },
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending':
      return 'warning'
    case 'in_progress':
      return 'info'
    case 'completed':
      return 'success'
    default:
      return 'grey'
  }
}

const getStatusName = (status: string) => {
  switch (status) {
    case 'pending':
      return '审核中'
    case 'in_progress':
      return '已下发'
    case 'completed':
      return '已完成'
    default:
      return status
  }
}

const getProgressValue = (progress: string) => {
  const [completed, total] = progress.split('/').map(Number)
  return ((total - completed) / total) * 100
}

const getProgressColor = (progress: string) => {
  const [completed, total] = progress.split('/').map(Number)
  if (completed === total) return 'success'
  if (completed > 0) return 'info'
  return 'warning'
}

const goToTaskDetail = (task: Task) => {
  router.push(`/task/${task.review_request_id}`)
}

// 时间验证相关
const timeError = ref('')

// 处理快速选择时间范围变化
const handleTimeRangeChange = (value: string | null) => {
  if (value) {
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

// 处理自定义时间变化
const handleCustomTimeChange = () => {
  filters.value.timeRange = null
  
  if (!filters.value.startDate || !filters.value.endDate) {
    timeError.value = '开始时间和结束时间不能为空'
    return
  }

  const startTime = new Date(filters.value.startDate).getTime()
  const endTime = new Date(filters.value.endDate).getTime()
  
  if (startTime >= endTime) {
    timeError.value = '开始时间必须早于结束时间'
  } else {
    timeError.value = ''
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.value = {
    status: null,
    timeRange: null,
    startDate: null,
    endDate: null
  }
  timeError.value = ''
  currentPage.value = 1
  pageSize.value = 10
  fetchTasks(1, 10)
  showFilterDialog.value = false
}

// 应用筛选条件
const applyFilters = () => {
  if (timeError.value) {
    return
  }
  
  currentPage.value = 1
  pageSize.value = 10
  fetchTasks(1, 10)
  showFilterDialog.value = false
}

// 从后端获取任务数据
const fetchTasks = async (page: number, pageSize: number) => {
  loading.value = true
  try {
    // 计算时间筛选
    let startTimeFilter: string | undefined
    let endTimeFilter: string | undefined
    if (filters.value.timeRange) {
      const now = Date.now()
      const ranges: Record<string, number> = {
        '1d': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
        '90d': 90 * 24 * 60 * 60 * 1000,
        '365d': 365 * 24 * 60 * 60 * 1000
      }
      const rangeMs = ranges[filters.value.timeRange as keyof typeof ranges]
      startTimeFilter = formatDateFilter(now - rangeMs)
      endTimeFilter = formatDateFilter(now)
    } else if (filters.value.startDate && filters.value.endDate) {
      startTimeFilter = formatDateFilter(new Date(filters.value.startDate).getTime())
      endTimeFilter = formatDateFilter(new Date(filters.value.endDate).getTime())
    }

    const params = {
      page,
      page_size: pageSize,
      status: filters.value.status || '',
      startTime: startTimeFilter,
      endTime: endTimeFilter
    }
    const response = await publisherApi.getPublisherReviewTasks(params)
    const { tasks: taskList, current_page, total_pages, total_count } = response.data
    
    tasks.value = taskList.map((task: any) => ({
      review_request_id: task.review_request_id,
      request_time: task.request_time,
      status: task.status,
      progress: task.progress
    }))
    
    currentPage.value = current_page
    totalPages.value = total_pages
    totalTasks.value = total_count
  } catch (error) {
    console.error('获取任务列表失败:', error)
    snackbar.showMessage('获取任务列表失败', 'error')
  } finally {
    loading.value = false
  }
}

// 处理页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchTasks(page, pageSize.value)
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks(1, size)
}

// 时间格式化，用于筛选条件
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

// 初始化
onMounted(() => {
  fetchTasks(currentPage.value, pageSize.value)
})
</script>

<style scoped>
.v-card {
  border-radius: 12px;
  overflow: hidden;
}

.status-chip {
  font-size: 12px;
  padding: 0 12px;
  font-weight: 500;
}

.v-btn.v-btn--size-small {
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 8px;
}

.v-btn--icon.v-btn--size-small .v-icon {
  font-size: 18px;
}

:deep(.v-data-table) {
  border-radius: 12px;
  width: 100%;
}

:deep(.v-data-table-header) {
  background-color: rgb(var(--v-theme-surface-variant));
}

:deep(.v-data-table-header th) {
  font-weight: 600;
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
}

:deep(.v-data-table__tr td) {
  white-space: nowrap;
}

:deep(.v-data-table__tr:hover) {
  background-color: rgba(var(--v-theme-on-surface), 0.04);
}

:deep(.v-chip) {
  font-weight: 500;
}

:deep(.v-text-field .v-field__input) {
  min-height: 40px;
}

:deep(.v-btn--variant-outlined) {
  border-color: rgb(var(--v-theme-outline));
}

:deep(.v-select .v-field__input) {
  min-height: 40px;
}

:deep(.v-select .v-field__append-inner) {
  padding-top: 0;
}

:deep(.v-progress-linear) {
  border-radius: 10px;
}

:deep(.v-progress-linear__content) {
  color: white;
  font-weight: 500;
}
</style>