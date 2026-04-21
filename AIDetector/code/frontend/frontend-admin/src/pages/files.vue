<template>
  <v-container>
    <!-- 标题 -->
    <v-row class="mb-6">
      <v-col>
        <h1 class="text-h4 font-weight-bold">图像管理</h1>
      </v-col>
    </v-row>

    <!-- 搜索和筛选区域 -->
    <v-row class="mb-4 align-center">
      <v-col cols="12" sm="8" md="6">
        <!-- 搜索出版社 -->
        <v-autocomplete
          v-model="searchSelectedUser"
          :items="searchUsersList"
          :loading="loadingSearchUsers"
          v-model:search="searchQuery"
          item-title="username"
          item-value="id"
          label="搜索编辑名"
          prepend-icon="mdi-magnify"
          return-object
          clearable
          hide-details
          @update:search="searchUsersForTable"
          @update:model-value="handleSearchSelection"
        >
          <template v-slot:selection="{ item }">
            <v-chip class="ma-1">
              {{ item.raw.username }}
              <v-avatar start size="24" class="mr-2">
                <v-img :src="getImageUrl(item.raw.avatar)" cover></v-img>
              </v-avatar>
            </v-chip>
          </template>
          <template v-slot:item="{ props, item }">
            <v-list-item v-bind="props" :title="item.raw.username" :subtitle="item.raw.email">
              <template v-slot:prepend>
                <v-avatar size="24" class="mr-2">
                  <v-img :src="getImageUrl(item.raw.avatar)" cover></v-img>
                </v-avatar>
              </template>
            </v-list-item>
          </template>
        </v-autocomplete>
      </v-col>

      <v-col v-if="currentUser?.admin_type == 'software_admin'" cols="12" sm="4" md="3">
        <!-- 搜索组织 -->
        <v-text-field
          v-model="searchSelectedOrg"
          label="搜索组织"
          prepend-icon="mdi-office-building"
          clearable
          hide-details
          @update:model-value="handleSearchSelection"
        ></v-text-field>
      </v-col>

      <!-- spacer 自动填充空位 -->
      <v-spacer></v-spacer>

      <!-- 筛选按钮，始终靠右 -->
      <v-col cols="auto">
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
        :items="files"
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
              共 {{ totalFiles }} 条记录
            </div>
          </div>
        </template>

        <template v-slot:item.subject="{ item }">
          <v-chip
            :color="getSubjectColor(item.subject)"
            size="small"
            class="subject-chip"
          >
            {{ getSubjectName(item.subject) }}
          </v-chip>
        </template>

        <template v-slot:item.uploadTime="{ item }">
          {{ formatTime(item.uploadTime) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon
            variant="text"
            size="small"
            color="primary"
            class="mr-2"
            @click="openDetailDialog(item)"
          >
            <v-icon>mdi-eye</v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="small"
            color="error"
            @click="openDeleteDialog(item)"
          >
            <v-icon>mdi-delete</v-icon>
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
              v-model="filters.subject"
              :items="subjectOptions"
              item-title="title"
              item-value="value"
              label="学科"
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

    <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">确认删除</v-card-title>
        <v-card-text>
          确定要删除该上传记录吗？此操作不可撤销。
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" @click="deleteFile">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 详情抽屉 -->
    <v-navigation-drawer
      v-model="showDetailDialog"
      temporary
      location="right"
      width="800"
    >
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-bold">图片详情</span>
        <v-btn icon @click="closeDetailDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- 筛选区域 -->
        <v-row class="mb-4">
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="detailFilters.isDetect"
              :items="[
                { title: '全部', value: 'all' },
                { title: '已检测', value: 'true' },
                { title: '未检测', value: 'false' }
              ]"
              item-title="title"
              item-value="value"
              label="AI检测状态"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="detailFilters.isReview"
              :items="[
                { title: '全部', value: 'all' },
                { title: '已审核', value: 'true' },
                { title: '未审核', value: 'false' }
              ]"
              item-title="title"
              item-value="value"
              label="人工审核状态"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="detailFilters.isFake"
              :disabled="detailFilters.isDetect !== 'true'"
              :items="[
                { title: '全部', value: 'all' },
                { title: '真实', value: 'true' },
                { title: '虚假', value: 'false' },
              ]"
              item-title="title"
              item-value="value"
              label="检测结果"
              hide-details
            ></v-select>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-btn color="primary" @click="handleDetailFilterChange">确认筛选</v-btn>
            <v-btn color="grey" variant="text" @click="resetDetailFilters" class="ml-2">重置</v-btn>
          </v-col>
        </v-row>

        <!-- 图片网格 -->
        <v-row>
          <v-col
            v-for="(image, index) in detailImages"
            :key="index"
            cols="12"
            sm="6"
            md="3"
            lg="3"
          >
            <v-card class="image-card" @click="openImageDialog(image)">
              <v-img
                :src="getImageUrl(image.url)"
                aspect-ratio="1"
                cover
                class="image-thumbnail"
              >
                <template v-slot:placeholder>
                  <v-row class="fill-height ma-0" align="center" justify="center">
                    <v-progress-circular indeterminate color="grey-lighten-5"></v-progress-circular>
                  </v-row>
                </template>
              </v-img>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn icon color="error" @click.stop="deleteListImage(image)">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-navigation-drawer>

    <!-- 图片详情对话框 -->
    <v-dialog v-model="showImageDialog" max-width="800">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">图片详情</v-card-title>
        <v-card-text>
          <div class="d-flex flex-column align-center">
            <div class="image-container">
              <v-img
                :src="selectedImage && selectedImage.url ? getImageUrl(selectedImage.url) : ''"
                :max-height="windowHeight * 0.6"
                :max-width="windowWidth * 0.7"
                contain
                class="mb-4"
              >
                <template v-slot:placeholder>
                  <v-row class="fill-height ma-0" align="center" justify="center">
                    <v-progress-circular indeterminate color="grey-lighten-5"></v-progress-circular>
                  </v-row>
                </template>
              </v-img>
            </div>
            <div class="d-flex flex-column gap-2">
              <div class="d-flex align-center">
                <v-icon
                  :color="selectedImage?.isDetect === 'true' ? 'success' : 'error'"
                  size="small"
                  class="mr-1"
                >
                  {{ selectedImage?.isDetect === 'true' ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                <span>AI检测状态：{{ selectedImage?.isDetect === 'true' ? '已检测' : '未检测' }}</span>
              </div>
              <div class="d-flex align-center">
                <v-icon
                  :color="selectedImage?.isReview === 'true' ? 'success' : 'error'"
                  size="small"
                  class="mr-1"
                >
                  {{ selectedImage?.isReview === 'true' ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                <span>人工审核状态：{{ selectedImage?.isReview === 'true' ? '已审核' : '未审核' }}</span>
              </div>
              <div class="d-flex align-center">
                <v-icon
                  :color="selectedImage?.isFake === 'true' ? 'success' : 'error'"
                  size="small"
                  class="mr-1"
                >
                  {{ selectedImage?.isFake === 'true' ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
                <span>检测结果：{{ selectedImage?.isFake === 'true' ? '真实' : selectedImage?.isFake === 'false' ? '虚假' : '未检测' }}</span>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" @click="deleteDetailImage(selectedImage)">删除图片</v-btn>
          <v-btn color="grey" variant="text" @click="showImageDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSnackbarStore } from '@/stores/snackbar'
import fileApi from '@/api/file'
import userApi from '@/api/user'

const snackbar = useSnackbarStore()

interface File {
  id: number
  username: string
  organization: string
  subject: string
  uploadTime: number
  images: Image[]
}

interface Image {
  id: number
  url: string
  isDetect: string
  isReview: string
  isFake: string | null
}

interface User {
  id: number
  username: string
  email: string
  avatar: string
}

const headers = computed(() => {
  const baseHeaders = [
    { title: '编辑名', key: 'username', align: 'start' },
    { title: '学科', key: 'subject', align: 'start' },
    { title: '上传时间', key: 'uploadTime', align: 'center' },
    { title: '操作', key: 'actions', align: 'center', sortable: false },
  ]
  
  if (currentUser.value?.admin_type === 'software_admin') {
    baseHeaders.splice(1, 0, { title: '所属组织', key: 'organization', align: 'start' })
  }
  
  return baseHeaders
}) as any

// 分页相关
const files = ref<File[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalFiles = ref(0)
const totalPages = ref(1)

// 搜索相关
const searchSelectedUser = ref<User | null>(null)
const searchSelectedOrg = ref<string | null>(null)
const searchUsersList = ref<User[]>([])
const loadingSearchUsers = ref(false)
const searchQuery = ref('')

// 筛选相关
const showFilterDialog = ref(false)
const filters = ref<{
  subject: string | null
  timeRange: string | null
  startDate: string | null
  endDate: string | null
}>({
  subject: null,
  timeRange: null,
  startDate: null,
  endDate: null
})

const subjectOptions = [
  { title: '生物', value: 'Biology' },
  { title: '医学', value: 'Medicine' },
  { title: '化学', value: 'Chemistry' },
  { title: '图形学', value: 'Graphics' },
  { title: '其他', value: 'Other' }
]

const timeRangeOptions = [
  { title: '最近一天', value: '1d' },
  { title: '最近一周', value: '7d' },
  { title: '最近一月', value: '30d' },
  { title: '最近三月', value: '90d' },
  { title: '最近一年', value: '365d' }
]

// 详情相关
const showDetailDialog = ref(false)
const selectedFile = ref<File | null>(null)
const detailImages = ref<any[]>([])
const detailPage = ref(1)
const detailPageSize = ref(12)
const hasMoreImages = ref(false)
const loadingMoreImages = ref(false)

const detailFilters = ref<{
  isDetect: string
  isReview: string
  isFake: string
}>({
  isDetect: 'all',
  isReview: 'all',
  isFake: 'all',
})

// 图片查看相关
const showImageDialog = ref(false)
const selectedImage = ref<Image | null>(null)

// 添加窗口尺寸响应
const windowWidth = ref(window.innerWidth)
const windowHeight = ref(window.innerHeight)

// 监听窗口大小变化
onMounted(() => {
  window.addEventListener('resize', () => {
    windowWidth.value = window.innerWidth
    windowHeight.value = window.innerHeight
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', () => {
    windowWidth.value = window.innerWidth
    windowHeight.value = window.innerHeight
  })
})

// 处理搜索选择
const handleSearchSelection = () => {
  searchQuery.value = ''
  fetchFiles(currentPage.value, pageSize.value)
}

// 搜索用户（用于表格）
const searchUsersForTable = async (query: string) => {
  if (!query) {
    searchUsersList.value = []
    return
  }
  
  loadingSearchUsers.value = true
  try {
    const response = await userApi.getUsers({ query, page: 1, page_size: 10, role: 'publisher' })
    searchUsersList.value = response.data.users || []
  } catch (error) {
    console.error('搜索用户失败:', error)
    snackbar.showMessage('搜索用户失败', 'error')
  } finally {
    loadingSearchUsers.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  currentPage.value = 1
  pageSize.value = 10
  fetchFiles(1, 10)
}

// 处理页码变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchFiles(page, pageSize.value)
}

// 处理每页数量变化
const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchFiles(1, size)
}

// 处理时间范围变化
const handleTimeRangeChange = (value: string | null) => {
  if (value) {
    filters.value.startDate = null
    filters.value.endDate = null
    timeError.value = ''
  }
}

// 处理自定义时间变化
const timeError = ref('')
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
    subject: null,
    timeRange: null,
    startDate: null,
    endDate: null
  }
  timeError.value = ''
  currentPage.value = 1
  pageSize.value = 10
  fetchFiles(1, 10)
  showFilterDialog.value = false
}

// 应用筛选条件
const applyFilters = () => {
  if (timeError.value) {
    return
  }
  
  currentPage.value = 1
  pageSize.value = 10
  fetchFiles(1, 10)
  showFilterDialog.value = false
}

// 打开详情抽屉
const openDetailDialog = async (file: File) => {
  selectedFile.value = file
  showDetailDialog.value = true
  detailPage.value = 1
  detailImages.value = []
  await fetchDetailImages()
  document.querySelector('.v-navigation-drawer__content')?.addEventListener('scroll', handleScroll)
}

// 获取详情图片
const fetchDetailImages = async () => {
  if (!selectedFile.value) return
  
  loadingMoreImages.value = true
  try {
    const response = await fileApi.getFileImages(selectedFile.value.id, {
      page: detailPage.value,
      page_size: detailPageSize.value,
      isDetect: detailFilters.value.isDetect,
      isReview: detailFilters.value.isReview,
      isFake: detailFilters.value.isFake
    })
    
    const { imgs, has_next } = response.data
    if (detailPage.value === 1) {
      detailImages.value = imgs.map((img: any) => ({
        id: img.img_id,
        url: img.img_url,
        isDetect: img.isDetect,
        isReview: img.isReview,
        isFake: img.isFake
      }))
    } else {
      detailImages.value.push(...imgs.map((img: any) => ({
        id: img.img_id,
        url: img.img_url,
        isDetect: img.isDetect,
        isReview: img.isReview,
        isFake: img.isFake
      })))
    }
    
    hasMoreImages.value = has_next
  } catch (error) {
    console.error('获取图片详情失败:', error)
    snackbar.showMessage('获取图片详情失败', 'error')
  } finally {
    loadingMoreImages.value = false
  }
}

// 加载更多图片
const loadMoreImages = async () => {
  detailPage.value++
  await fetchDetailImages()
}

// 处理筛选变化
const handleDetailFilterChange = () => {
  detailPage.value = 1
  detailImages.value = []
  fetchDetailImages()
}

// 重置详情筛选条件
const resetDetailFilters = () => {
  detailFilters.value = {
    isDetect: 'all',
    isReview: 'all',
    isFake: 'all'
  }
  detailPage.value = 1
  detailImages.value = []
  fetchDetailImages()
}

// 打开删除对话框
const showDeleteDialog = ref(false)
const openDeleteDialog = (file: File) => {
  selectedFile.value = file
  showDeleteDialog.value = true
}


const getImageUrl =(url:string)=>{
  return import.meta.env.VITE_API_URL + url
}


// 删除文件
const deleteFile = async () => {
  if (selectedFile.value) {
    try {
      // 调用后端删除上传记录 API
      const id = selectedFile.value.id
      await fileApi.deleteFile(id)
      // 从列表中移除已删除的文件
      files.value = files.value.filter(f => f.id !== id)
      snackbar.showMessage('删除成功', 'success')
    } catch (error) {
      console.error('删除失败:', error)
      snackbar.showMessage('删除失败', 'error')
    }
  }
  showDeleteDialog.value = false
}

// 删除列表中的单张图片
const deleteListImage = async (image: Image) => {
  if (!selectedFile.value) return
  
  try {
    await fileApi.deleteImage(image.id)
    // 从列表中移除已删除的图片
    selectedFile.value.images = selectedFile.value.images.filter(
      img => img.id !== image.id
    )
    // 同时从详情图片列表中移除
    detailImages.value = detailImages.value.filter(img => img.id !== image.id)
    // 如果当前正在查看的图片被删除，关闭图片对话框
    if (selectedImage.value?.id === image.id) {
      showImageDialog.value = false
    }
    snackbar.showMessage('图片删除成功', 'success')
  } catch (error) {
    console.error('删除图片失败:', error)
    snackbar.showMessage('删除图片失败', 'error')
  }
}

// 删除详情对话框中的单张图片
const deleteDetailImage = async (image: Image | null) => {
  if (!image) return
  
  try {
    await fileApi.deleteImage(image.id)
    // 从详情图片列表中移除已删除的图片
    detailImages.value = detailImages.value.filter(img => img.id !== image.id)
    // 同时从文件图片列表中移除
    if (selectedFile.value) {
      selectedFile.value.images = selectedFile.value.images.filter(
        img => img.id !== image.id
      )
    }
    snackbar.showMessage('图片删除成功', 'success')
    showImageDialog.value = false
  } catch (error) {
    console.error('删除图片失败:', error)
    snackbar.showMessage('删除图片失败', 'error')
  }
}

// 打开图片对话框
const openImageDialog = (image: Image) => {
  selectedImage.value = image
  showImageDialog.value = true
}

// 删除单张图片（保留原有函数作为兼容）
const deleteSingleImage = async (image: Image) => {
  if (showImageDialog.value) {
    await deleteDetailImage(image)
  } else {
    await deleteListImage(image)
  }
}

// 格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

// 时间筛选格式化，用于生成后端可识别的时间字符串
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

// 从后端获取文件数据
const fetchFiles = async (page: number, pageSize: number) => {
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
      query: searchSelectedUser.value?.username || '',
      organization: searchSelectedOrg.value || '',
      categories: filters.value.subject || '',
      startTime: startTimeFilter,
      endTime: endTimeFilter
    }
    const response = await fileApi.getFiles(params)
    const { files: fileList, current_page, total_pages, total_files } = response.data
    
    // 转换后端数据格式为前端格式
    files.value = fileList.map((file: any) => ({
      id: file.id,
      username: file.username,
      organization: file.organization || '未知组织',
      subject: file.tag,
      uploadTime: new Date(file.upload_time).getTime(),
      images: [
        {
          id: file.id,
          url: file.file_url || '',
          isDetect: file.ai_checked ? 'true' : 'false',
          isReview: file.manually_checked ? 'true' : 'false',
          isFake: file.result ? 'true' : file.result === false ? 'false' : null,
        }
      ]
    }))
    
    currentPage.value = current_page
    totalPages.value = total_pages
    totalFiles.value = total_files
  } catch (error) {
    console.error('获取文件数据失败:', error)
    snackbar.showMessage('获取文件数据失败', 'error')
  } finally {
    loading.value = false
  }
}

// 当前用户
const currentUser = ref<{ 
  email: string;
  admin_type?: string;
} | null>(null)



// 初始化
onMounted(async () => {
  try {
    const res = await userApi.getUserInfo()
    currentUser.value = res.data
  } catch (error) {
    console.error('获取当前用户信息失败:', error)
  }
  fetchFiles(currentPage.value, pageSize.value)
})

const getSubjectColor = (subject: string) => {
  switch (subject) {
    case 'Biology':
      return 'success'
    case 'Medicine':
      return 'info'
    case 'Chemistry':
      return 'warning'
    case 'Graphics':
      return 'primary'
    case 'Other':
      return 'grey'
    default:
      return 'grey'
  }
}

const getSubjectName = (subject: string) => {
  switch (subject) {
    case 'Biology':
      return '生物'
    case 'Medicine':
      return '医学'
    case 'Chemistry':
      return '化学'
    case 'Graphics':
      return '图形学'
    case 'Other':
      return '其他'
    default:
      return subject
  }
}

// 关闭详情抽屉
const closeDetailDialog = () => {
  showDetailDialog.value = false
  detailFilters.value = {
    isDetect: 'all',
    isReview: 'all',
    isFake: 'all'
  }
  detailPage.value = 1
  detailImages.value = []
  document.querySelector('.v-navigation-drawer__content')?.removeEventListener('scroll', handleScroll)
}

const handleScroll = () => {
  const drawer = document.querySelector('.v-navigation-drawer__content')
  if (drawer && hasMoreImages.value && !loadingMoreImages.value) {
    const { scrollTop, scrollHeight, clientHeight } = drawer
    if (scrollHeight - scrollTop <= clientHeight + 100) {
      loadMoreImages()
    }
  }
}
</script>

<style scoped>
.v-card {
  border-radius: 12px;
  overflow: hidden;
}

.subject-chip {
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

.image-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.image-card:hover {
  transform: scale(1.02);
}

.image-thumbnail {
  border-radius: 8px;
}

:deep(.v-avatar) {
  overflow: hidden;
  border-radius: 50%;
}

:deep(.v-avatar .v-img) {
  height: 100%;
  width: 100%;
  object-fit: cover;
}

.image-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 16px;
}

:deep(.v-img) {
  transition: transform 0.2s;
}

:deep(.v-img:hover) {
  transform: scale(1.02);
}
</style>
