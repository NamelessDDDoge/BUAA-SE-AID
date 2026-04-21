<template>
  <v-container>
    <!-- 标题 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">人工审核审批</h1>
      </v-col>
    </v-row>

    <!-- 搜索和筛选区域 -->
    <v-row class="mb-4">
      <v-col cols="12" sm="8" md="6">
        <v-text-field
          v-model="searchQuery"
          label="搜索编辑"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          class="search-input"
          @keyup.enter="handleSearch"
          @click:append-inner="handleSearch"
          @click:clear="handleSearch"
          placeholder="请输入编辑名称"
        ></v-text-field>
      </v-col>
      <v-col cols="12" sm="4" md="6" class="d-flex justify-end">
        <v-btn 
          color="primary" 
          class="text-none mr-2" 
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
        :items="requests"
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
              共 {{ totalRequests }} 条记录
            </div>
          </div>
        </template>

        <template v-slot:item.avatar="{ item }">
          <v-avatar size="40">
            <v-img :src="item.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'" :alt="item.username"></v-img>
          </v-avatar>
        </template>

        <template v-slot:item.state="{ item }">
          <v-chip
            :color="getStateColor(item.state)"
            size="small"
            class="state-chip"
          >
            {{ getStateName(item.state) }}
          </v-chip>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon
            variant="text"
            size="small"
            color="primary"
            class="mr-2"
            @click="openReviewDialog(item)"
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
              label="审核状态"
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

    <!-- 审核详情对话框 -->
    <v-dialog v-model="showReviewDialog" max-width="800">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">审核详情</v-card-title>
        <v-card-text>
          <div v-if="selectedRequest" class="d-flex flex-column gap-4">
            <div class="d-flex align-center">
              <v-avatar size="40" class="mr-4">
                <v-img :src="selectedRequest.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'" :alt="selectedRequest.username"></v-img>
              </v-avatar>
              <div>
                <div class="text-h6">{{ selectedRequest.username }}</div>
                <div class="text-caption text-medium-emphasis">{{ formatTime(selectedRequest.time) }}</div>
              </div>
            </div>
            
            <v-divider></v-divider>

            <div class="d-flex flex-column gap-2">
              <div class="text-subtitle-1 font-weight-bold">审核状态</div>
              <v-chip
                :color="getStateColor(selectedRequest.state)"
                size="small"
                class="state-chip"
              >
                {{ getStateName(selectedRequest.state) }}
              </v-chip>
            </div>

            <v-divider></v-divider>

            <div v-if="reviewDetails" class="d-flex flex-column gap-4">
              <div class="d-flex flex-column gap-2">
                <div class="text-subtitle-1 font-weight-bold">相关图片</div>
                <div class="d-flex flex-wrap gap-2">
                  <v-img
                    v-for="img in reviewDetails.imgs"
                    :key="img.id"
                    :src="getImageUrl(img.url)"
                    width="200"
                    height="200"
                    cover
                    class="rounded-lg"
                  ></v-img>
                </div>
              </div>

              <div class="d-flex flex-column gap-2">
                <div class="text-subtitle-1 font-weight-bold">审核人列表</div>
                <div class="d-flex flex-wrap gap-4">
                  <div v-for="person in reviewDetails.persons" :key="person.id" class="d-flex align-center">
                    <v-avatar size="32" class="mr-2">
                      <v-img :src="getImageUrl(person.avatar)" :alt="person.username"></v-img>
                    </v-avatar>
                    <span>{{ person.username }}</span>
                  </div>
                </div>
              </div>

              <div v-if="reviewDetails.reason" class="d-flex flex-column gap-2">
                <div class="text-subtitle-1 font-weight-bold">申请理由</div>
                <div class="text-body-1">{{ reviewDetails.reason }}</div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" variant="text" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(0)">拒绝</v-btn>
          <v-btn color="success" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(1)">通过</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 拒绝理由对话框 -->
    <v-dialog v-model="showRejectDialog" max-width="500">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">拒绝理由</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="rejectReason"
            label="请输入拒绝理由"
            rows="3"
            hide-details
            variant="outlined"
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showRejectDialog = false">取消</v-btn>
          <v-btn color="error" @click="handleReviewRequest(0)">确认拒绝</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import reviewApi from '@/api/review'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

interface ReviewRequest {
  id: number
  username: string
  avatar: string
  state: string
  file_type: string
  time: string
}

const headers = [
  { title: '头像', key: 'avatar', align: 'center', sortable: false },
  { title: '编辑', key: 'username', align: 'start' },
  { title: '审核状态', key: 'state', align: 'center' },
  { title: '提交时间', key: 'time', align: 'center' },
  { title: '操作', key: 'actions', align: 'center', sortable: false },
] as const

// 分页相关
const requests = ref<ReviewRequest[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalRequests = ref(0)
const totalPages = ref(1)

// 搜索相关
const searchQuery = ref('')

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
  { title: '未处理', value: 'pending' },
  { title: '已拒绝', value: 'refused' },
  { title: '已通过', value: 'accepted' }
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]


const getImageUrl =(url:string)=>{
  return import.meta.env.VITE_API_URL + url
}

// 审核详情对话框相关
const showReviewDialog = ref(false)
const selectedRequest = ref<ReviewRequest | null>(null)
const reviewDetails = ref<{
  imgs: Array<{ id: number, url: string }>
  persons: Array<{ id: number, username: string, avatar: string }>
  reason: string
} | null>(null)
const rejectReason = ref('')
const showRejectDialog = ref(false)

const getStateColor = (state: string) => {
  switch (state) {
    case 'pending':
      return 'warning'
    case 'refused':
      return 'error'
    case 'accepted':
      return 'success'
    default:
      return 'grey'
  }
}

const getStateName = (state: string) => {
  switch (state) {
    case 'pending':
      return '未处理'
    case 'refused':
      return '已拒绝'
    case 'accepted':
      return '已通过'
    default:
      return state
  }
}

const formatTime = (timestamp: string) => {
  return timestamp // 后端返回的时间格式已经是正确的，直接显示
}

const openReviewDialog = async (request: ReviewRequest) => {
  selectedRequest.value = request
  try {
    const response = await reviewApi.getReviewRequestDetails(request.id)
    reviewDetails.value = response.data
    showReviewDialog.value = true
  } catch (error) {
    console.error('获取审核详情失败:', error)
    snackbar.showMessage('获取审核详情失败', 'error')
  }
}

const handleReviewRequest = async (choice: number) => {
  if (choice === 0 && !rejectReason.value) {
    showRejectDialog.value = true
    return
  }

  try {
    await reviewApi.handleReviewRequest(selectedRequest.value!.id, {
      choice,
      reason: rejectReason.value
    })
    snackbar.showMessage(choice === 1 ? '已通过审核' : '已拒绝审核', 'success')
    showReviewDialog.value = false
    showRejectDialog.value = false
    rejectReason.value = ''
    fetchRequests(currentPage.value, pageSize.value)
  } catch (error) {
    console.error('处理审核请求失败:', error)
    snackbar.showMessage('处理审核请求失败', 'error')
  }
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
  fetchRequests(1, 10)
  showFilterDialog.value = false
}

// 应用筛选条件
const applyFilters = () => {
  if (timeError.value) {
    return
  }
  
  currentPage.value = 1
  pageSize.value = 10
  fetchRequests(1, 10)
  showFilterDialog.value = false
}

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1
  pageSize.value = 10
  fetchRequests(1, 10)
}

// 从后端获取审核请求数据
const fetchRequests = async (page: number, pageSize: number) => {
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
      query: searchQuery.value || '',
      status: filters.value.status || '',
      startTime: startTimeFilter,
      endTime: endTimeFilter
    }
    const response = await reviewApi.getReviewRequests(params)
    const { requests: requestList, current_page, total_pages, total_requests } = response.data
    
    requests.value = requestList.map((request: any) => ({
      id: request.id,
      username: request.username,
      avatar: import.meta.env.VITE_API_URL + request.avatar || '',
      state: request.state,
      file_type: request.file_type,
      time: request.time
    }))
    
    currentPage.value = current_page
    totalPages.value = total_pages
    totalRequests.value = total_requests
  } catch (error) {
    console.error('获取审核请求失败:', error)
    snackbar.showMessage('获取审核请求失败', 'error')
  } finally {
    loading.value = false
  }
}

// 处理页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchRequests(page, pageSize.value)
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchRequests(1, size)
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
  fetchRequests(currentPage.value, pageSize.value)
})
</script>

<style scoped>
.v-card {
  border-radius: 12px;
  overflow: hidden;
}

.state-chip {
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

.search-input {
  max-width: 400px;
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
</style> 