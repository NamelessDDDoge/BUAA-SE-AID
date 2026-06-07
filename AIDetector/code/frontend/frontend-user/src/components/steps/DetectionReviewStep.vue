<template>
  <v-container class="mt-8">
    <v-row>
      <v-col cols="12">
        <!-- 顶部信息卡片 -->
        <v-card class="mb-8 pa-6" elevation="2" rounded="lg">
          <v-row>
            <!-- 左侧进度环 -->
            <v-col cols="4" class="border-r">
              <div class="detection-summary">
                <v-progress-circular :model-value="(detectionResult.fakeCount / detectionResult.totalCount) * 100"
                  :size="160" :width="12" color="primary" class="custom-progress">
                  <div class="progress-content">
                    <div class="text-h4 font-weight-bold responsive-text">{{ detectionResult.fakeCount }}/{{
                      detectionResult.totalCount }}</div>
                    <div class="text-subtitle-2 mt-1 responsive-text">造假图片数量</div>
                  </div>
                </v-progress-circular>
              </div>
            </v-col>

            <!-- 右侧信息和按钮 -->
            <v-col cols="8" class="pl-8">
              <div class="d-flex flex-column justify-space-between h-100">
                <!-- 任务信息 -->
                <div class="task-info mb-8">
                  <div class="text-h6 mb-4">任务信息</div>
                  <div class="d-flex flex-column gap-2">
                    <div class="info-item d-flex align-center" :class="isDarkMode ? 'info-item-dark' : ''">
                      <v-icon :color="isDarkMode ? 'grey-lighten-1' : 'grey-darken-2'"
                        class="mr-2">mdi-clock-outline</v-icon>
                      <span class="text-body-1">检测时间：{{ formatDateTime(detectionResult.detectionTime) }}</span>
                    </div>
                    <div class="info-item d-flex align-center" :class="isDarkMode ? 'info-item-dark' : ''">
                      <v-icon :color="isDarkMode ? 'grey-lighten-1' : 'grey-darken-2'" class="mr-2">mdi-pound</v-icon>
                      <span class="text-body-1">检测编号：{{ props.task_id }}</span>
                    </div>
                  </div>
                </div>

                <!-- 操作按钮 -->
                <div class="d-flex flex-wrap gap-4">
                  <v-btn color="primary" variant="elevated" class="px-8 py-2" rounded="pill"
                    prepend-icon="mdi-file-document-outline" elevation="2" @click="downloadReport">
                    查看报告
                  </v-btn>
                  <v-btn :color="isDarkMode ? 'green-darken-2' : 'success'" variant="elevated" class="px-8 py-2"
                    rounded="pill" prepend-icon="mdi-account-check-outline" elevation="2" @click="scrollToReviewConfig">
                    申请人工审核
                  </v-btn>
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card>

        <!-- 图片展示区域 -->
        <v-row>
          <v-col cols="12">
            <!-- 疑似造假图片卡片 -->
            <v-card class="mb-6" elevation="2" rounded="lg">
              <v-card-title class="d-flex justify-space-between pa-6">
                <div class="d-flex align-center">
                  <v-icon color="error" class="mr-2">mdi-alert-circle</v-icon>
                  <span class="text-h6">疑似造假图片</span>
                  <v-chip color="error" class="ml-4" size="small">{{ selectedFakeCount }}/{{
                    detectionResult.fakeImages.length }}</v-chip>
                </div>
                <v-btn color="error" variant="text" @click="selectAllFake">
                  {{ isAllFakeSelected ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text class="pa-6">
                <v-sheet class="overflow-x-auto">
                  <div class="d-flex image-grid">
                    <v-hover v-for="(img, index) in detectionResult.fakeImages" :key="index"
                      v-slot="{ isHovering, props }">
                      <v-card v-bind="props" class="ma-2 position-relative" width="200" height="200" elevation="2"
                        rounded="lg" :class="{ 'selected-image-card': img.selected }" @click="toggleImageSelection(img, 'fake')">
                        <v-img :src="getImageUrl(img.image_url)" cover height="100%">
                          <div class="image-overlay" v-if="isHovering || img.selected">
                            <div class="d-flex flex-column align-center gap-4">
                              <v-checkbox :model-value="img.selected" color="primary" class="image-checkbox"
                                @click.stop="toggleImageSelection(img, 'fake')"></v-checkbox>
                              <v-btn icon="mdi-magnify" variant="text" color="white" size="large"
                                @click.stop="viewImageDetail(img)"></v-btn>
                            </div>
                          </div>
                        </v-img>
                      </v-card>
                    </v-hover>
                  </div>
                </v-sheet>
              </v-card-text>
            </v-card>

            <!-- 正常图片卡片 -->
            <v-card elevation="2" rounded="lg">
              <v-card-title class="d-flex justify-space-between pa-6">
                <div class="d-flex align-center">
                  <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
                  <span class="text-h6">正常图片</span>
                  <v-chip color="success" class="ml-4" size="small">{{ selectedRealCount }}/{{
                    detectionResult.realImages.length }}</v-chip>
                </div>
                <v-btn color="success" variant="text" @click="selectAllReal">
                  {{ isAllRealSelected ? '取消全选' : '全选' }}
                </v-btn>
              </v-card-title>
              <v-card-text class="pa-6">
                <v-sheet class="overflow-x-auto">
                  <div class="d-flex image-grid">
                    <v-hover v-for="(img, index) in detectionResult.realImages" :key="index"
                      v-slot="{ isHovering, props }">
                      <v-card v-bind="props" class="ma-2 position-relative" width="200" height="200" elevation="2"
                        rounded="lg" :class="{ 'selected-image-card': img.selected }" @click="toggleImageSelection(img, 'real')">
                        <v-img :src="getImageUrl(img.image_url)" cover height="100%">
                          <div class="image-overlay" v-if="isHovering || img.selected">
                            <div class="d-flex flex-column align-center gap-4">
                              <v-checkbox :model-value="img.selected" color="primary" class="image-checkbox"
                                @click.stop="toggleImageSelection(img, 'real')"></v-checkbox>
                              <v-btn icon="mdi-magnify" variant="text" color="white" size="large"
                                @click.stop="viewImageDetail(img)"></v-btn>
                            </div>
                          </div>
                        </v-img>
                      </v-card>
                    </v-hover>
                  </div>
                </v-sheet>
              </v-card-text>
            </v-card>

            <!-- 人工审核配置区域 -->
            <v-card ref="reviewConfigRef" class="mt-6 review-config-card" elevation="2" rounded="lg">
              <v-card-title class="pa-6 d-flex align-center flex-wrap ga-3">
                <span class="text-h6">人工审核配置</span>
                <v-chip color="primary" variant="tonal" size="small">已选图片 {{ selectedImageCount }}</v-chip>
                <v-chip color="teal" variant="tonal" size="small">审核人员 {{ selectedPeople }}</v-chip>
              </v-card-title>
              <v-card-text class="pa-6">
                <v-alert type="info" variant="tonal" class="mb-4">
                  {{ reviewSubmitHint }}
                </v-alert>
                <div class="review-submit-row">
                  <v-autocomplete v-model="selectedPeopleList" :items="filteredPeople" :loading="isSearching"
                    v-model:search="searchQuery" item-title="username" item-value="id" label="选择审核人员（当前组织）" multiple chips
                    closable-chips hide-details variant="outlined" @update:search="searchPeople">
                    <template v-slot:chip="{ props, item }">
                      <v-chip v-bind="props" :prepend-avatar="getAvatar(item.raw.avatar)">
                        {{ item.raw.username }}
                      </v-chip>
                    </template>
                    <template v-slot:item="{ props, item }">
                      <v-list-item v-bind="props" :prepend-avatar="getAvatar(item.raw.avatar)"
                        :title="item.raw.username"></v-list-item>
                    </template>
                  </v-autocomplete>
                  <v-btn
                    color="success"
                    size="large"
                    min-width="150"
                    prepend-icon="mdi-send"
                    :disabled="!canSubmit"
                    :loading="submittingReview"
                    @click="submitReview"
                  >
                    提交人工审核
                  </v-btn>
                </div>
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
      </v-col>
    </v-row>

    <!-- 图片详情对话框 -->
    <v-dialog v-model="showImageDetail" max-width="1000">
      <v-card rounded="lg">
        <v-card-title class="pa-6 d-flex">
          <h1 class="text-h5">图片详情</h1>
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="toggleClose"></v-btn>
        </v-card-title>

        <v-card-text class="pa-6">
          <v-row>
            <!-- 图片展示区域 -->
            <v-col cols="12" md="6" class="pr-md-6">
              <div class="image-container" ref="imageContainer">
                <v-img :src="getSelectedImageUrl(selectedImage)" max-height="500" contain class="rounded-lg"
                  ref="mainImage"></v-img>

                <!-- 检测覆盖层 -->
                <transition name="fade">
                  <v-img v-if="activeOverlay && isOverlayVisible" :src="activeOverlay"
                    class="rounded-lg overlay-image"></v-img>
                </transition>
              </div>

              <div class="mt-6">
                <div class="d-flex flex-column gap-2">
                  <div class="info-item d-flex align-center">
                    <v-icon color="grey" class="mr-2">mdi-clock-outline</v-icon>
                    <span class="text-body-1">检测时间：{{ formatDateTime(detectionResult.detectionTime) }}</span>
                  </div>
                  <div class="info-item d-flex align-center">
                    <v-icon color="grey" class="mr-2">mdi-pound</v-icon>
                    <span class="text-body-1">检测编号：{{ props.task_id }}</span>
                  </div>
                </div>
              </div>
            </v-col>

            <!-- 右侧标签页 -->
            <v-col cols="12" md="6" class="pl-md-6">
              <v-tabs v-model="activeTab" color="primary">
                <v-tab value="analysis" style="font-size: 16px;">大模型</v-tab>
                <v-tab value="history" style="font-size: 16px;">深度学习</v-tab>
                <v-tab value="comments" style="font-size: 16px;">传统方法</v-tab>
              </v-tabs>

              <v-divider></v-divider>

              <v-window v-model="activeTab" class="mt-4">
                <v-window-item value="analysis">
                  <div class="d-flex align-center justify-space-between mb-4">
                    <div class="text-h6">大模型意见</div>
                    <v-btn v-if="activeOverlay" size="small" variant="outlined" color="primary" prepend-icon="mdi-eye"
                      @click="toggleLLM">
                      {{ isOverlayVisible ? '隐藏造假区域' : '展示造假区域' }}
                    </v-btn>
                  </div>

                  <v-card>
                    <v-card-text>
                      {{ llm }}
                    </v-card-text>
                  </v-card>
                </v-window-item>

                <v-window-item value="history">
                  <div class="text-h6 mb-4">深度学习模型结果</div>
                  <v-list class="elevation-1 rounded-lg">
                    <v-list-item-group>
                      <template v-for="(dimension, index) in urn" :key="dimension.method">
                        <v-list-item class="py-2 px-3">
                          <div class="d-flex align-center" style="gap: 24px; width: 100%;">
                            <div class="text-body-1 font-weight-medium" style="min-width: 100px;">
                              {{ dimension.method }}
                            </div>

                            <v-progress-circular :model-value="dimension.probability * 100"
                              :color="getProbabilityColor(dimension.probability)" size="40" width="5">
                              <span class="text-caption">{{ (dimension.probability * 100).toFixed(0) }}%</span>
                            </v-progress-circular>

                            <v-btn size="small" :color="dimension.visible ? 'error' : 'grey'" variant="tonal"
                              @click="toggleOverlay(dimension)" class="fake-area-btn ml-4">
                              <v-icon size="small" :icon="dimension.visible ? 'mdi-eye-off' : 'mdi-eye'"
                                class="mr-1"></v-icon>
                              {{ dimension.visible ? '隐藏造假区域' : '显示造假区域' }}
                            </v-btn>
                          </div>
                        </v-list-item>

                        <v-divider v-if="index < urn.length - 1"></v-divider>
                      </template>
                    </v-list-item-group>
                  </v-list>
                </v-window-item>

                <v-window-item value="comments">
                  <div class="text-h6 mb-4">传统方法结果</div>
                  <v-card class="mb-4" elevation="2">
                    <v-card-text>
                      <v-list-item>
                        <v-list-item-icon>
                          <v-icon :color="exif.photoshop_edited ? 'error' : 'success'">
                            {{ exif.photoshop_edited ? 'mdi-alert-circle' : 'mdi-check-circle' }}
                          </v-icon>
                        </v-list-item-icon>
                        <v-list-item-content>
                          <v-list-item-title>是否经过PS处理</v-list-item-title>
                          <v-list-item-subtitle>
                            <span :class="exif.photoshop_edited ? 'error--text' : 'success--text'">
                              {{ exif.photoshop_edited ? '检测到PS痕迹' : '未检测到PS痕迹' }}
                            </span>
                          </v-list-item-subtitle>
                        </v-list-item-content>
                      </v-list-item>

                      <v-divider class="my-2"></v-divider>

                      <v-list-item>
                        <v-list-item-icon>
                          <v-icon :color="exif.time_modified ? 'error' : 'success'">
                            {{ exif.time_modified ? 'mdi-alert-circle' : 'mdi-check-circle' }}
                          </v-icon>
                        </v-list-item-icon>
                        <v-list-item-content>
                          <v-list-item-title>是否经过时间修改</v-list-item-title>
                          <v-list-item-subtitle>
                            <span :class="exif.time_modified ? 'error--text' : 'success--text'">
                              {{ exif.time_modified ? '检测到时间篡改' : '未检测到时间修改' }}
                            </span>
                          </v-list-item-subtitle>
                        </v-list-item-content>
                      </v-list-item>
                    </v-card-text>
                  </v-card>
                </v-window-item>
              </v-window>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useTheme } from 'vuetify'
import { useSnackbarStore } from '@/stores/snackbar'
import publisher from '@/api/publisher'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useUserStore } from '@/stores/user'

interface Image {
  result_id: string
  image_url: string
  image_id: string
  selected?: boolean
}

interface DetectionResult {
  detectionTime: string
  detectionId: string
  totalCount: number
  fakeCount: number
  fakeImages: Image[]
  realImages: Image[]
}

interface SubMethod {
  method: string
  probability: number
  mask_image: string
  mask_matrix: any | null
  visible: boolean
}

interface Person {
  id: number
  username: string
  avatar: string
}

type SelectId = number | string

const router = useRouter()
const snackbar = useSnackbarStore()
const theme = useTheme()
const emit = defineEmits(['complete', 'update'])
const isDarkMode = computed(() => theme.global.current.value.dark)
const activeTab = ref('analysis')
const llm = ref('')
const llm_image = ref('')
const ela = ref()
const urn = ref<SubMethod[]>([])
const exif = ref()
const activeOverlay = ref()
const isOverlayVisible = ref(false)

// 审核人员相关
const searchQuery = ref('')
const isSearching = ref(false)
const allPeople = ref<Person[]>([])
const selectedPeopleList = ref<SelectId[]>([])
const reviewReason = ref('')
const reviewConfigRef = ref<HTMLElement | { $el?: HTMLElement } | null>(null)
const submittingReview = ref(false)

// 计算是否可以提交
const canSubmit = computed(() => {
  const hasSelectedImages = selectedFakeCount.value > 0 || selectedRealCount.value > 0
  return hasSelectedImages && selectedPeopleList.value.length > 0 && reviewReason.value.trim().length > 0
})

const selectedImageCount = computed(() => selectedFakeCount.value + selectedRealCount.value)

const reviewSubmitHint = computed(() => {
  if (!selectedImageCount.value) return '请先在上方选择需要复核的图片，选中后这里即可提交。'
  if (!selectedPeopleList.value.length) return `已选择 ${selectedImageCount.value} 张图片，请选择至少 1 名审核人员。`
  if (!reviewReason.value.trim()) return `已选择 ${selectedImageCount.value} 张图片、${selectedPeopleList.value.length} 名审核人员，请填写申请理由。`
  return `将提交 ${selectedImageCount.value} 张图片给 ${selectedPeopleList.value.length} 名审核人员。`
})

const scrollToReviewConfig = () => {
  const target = reviewConfigRef.value
  const element = target instanceof HTMLElement ? target : target?.$el
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 提交人工审核
const submitReview = async () => {
  if (!canSubmit.value) {
    snackbar.showMessage(reviewSubmitHint.value, 'warning')
    scrollToReviewConfig()
    return
  }
  if (submittingReview.value) return
  submittingReview.value = true
  try {
    const getImageId = (img: Image) => Number((img as Image & { img_id?: SelectId; id?: SelectId }).image_id ?? (img as Image & { img_id?: SelectId; id?: SelectId }).img_id ?? (img as Image & { img_id?: SelectId; id?: SelectId }).id)
    const reviewImages = [
      ...detectionResult.value.fakeImages.filter((img: Image) => img.selected).map(getImageId),
      ...detectionResult.value.realImages.filter((img: Image) => img.selected).map(getImageId)
    ].filter((id: number) => Number.isFinite(id) && id > 0)
    const reviewerIds = selectedPeopleList.value
      .map(id => Number(id))
      .filter((id: number) => Number.isFinite(id) && id > 0)

    if (reviewImages.length === 0) {
      snackbar.showMessage('请选择需要人工审核的图片', 'warning')
      return
    }
    if (reviewerIds.length === 0) {
      snackbar.showMessage('请选择审核人员', 'warning')
      return
    }

    const response = await publisher.dispatchAnnual({
      image_ids: reviewImages,
      reviewers: reviewerIds,
      reason: reviewReason.value.trim(),
    })
    snackbar.showMessage('已提交人工复查任务，请等待管理员审核', 'success')
    const reviewRequestId = response?.data?.review_request_id
    if (reviewRequestId) {
      router.push(`/task/${reviewRequestId}`)
      return
    }
    router.push('/annual')
  } catch (error: any) {
    let message = '提交人工复查任务失败'
    if (axios.isAxiosError(error)) {
      const data = error.response?.data
      if (typeof data?.error === 'string') {
        message = data.error
      } else if (typeof data?.message === 'string') {
        message = data.message
      } else if (typeof data?.detail === 'string') {
        message = data.detail
      } else if (error.code === 'ERR_NETWORK') {
        message = '网络连接失败，请检查后端服务是否可访问'
      }
    }
    snackbar.showMessage(message, 'error')
  } finally {
    submittingReview.value = false
  }
}

const toggleLLM = () => {
  isOverlayVisible.value = !isOverlayVisible.value
  activeOverlay.value = getImageUrl(llm_image.value)
}

const downloadReport = async () => {
  try {
    const response = await publisher.downloadReport(props.task_id)
    const contentDisposition = response.headers['content-disposition']

    let fileName = `task_${props.task_id}_report.pdf`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) fileName = match[1];
    }

    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    snackbar.showMessage('报告下载失败', 'error')
  }
}

const formatDateTime = (dateTime: string) => {
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

const detectionResult = ref<DetectionResult>({
  detectionTime: '',
  detectionId: '',
  totalCount: 0,
  fakeCount: 0,
  fakeImages: [],
  realImages: []
})

const props = withDefaults(defineProps<{
  task_id?: string
  detection_time?: string
}>(), {
  task_id: '',
  detection_time: ''
})

onMounted(async () => {
  try {
    const userStore = useUserStore()
    const response = await publisher.getReviewers({ publisher_id: userStore.id })
    allPeople.value = Array.isArray(response.data.reviewers) ? response.data.reviewers : []

    detectionResult.value.fakeImages = (await publisher.getFakeImage({ task_id: props.task_id, include_image: 1 })).data.results
    detectionResult.value.realImages = (await publisher.getNormalImage({ task_id: props.task_id, include_image: 1 })).data.results
    detectionResult.value.fakeCount = detectionResult.value.fakeImages.length
    detectionResult.value.totalCount = detectionResult.value.realImages.length + detectionResult.value.fakeCount
  } catch (error) {
    console.error('获取数据失败:', error)
    snackbar.showMessage('获取数据失败', 'error')
    allPeople.value = []
  }
})

const showImageDetail = ref(false)
const selectedImage = ref<Image | null>(null)

const fetchImageDetection = async (result_id: string) => {
  try {
    const response = (await publisher.getSingleImageResult(result_id)).data
    llm.value = response.llm
    llm_image.value = response.llm_image
    ela.value = response.ela_image
    urn.value = response.sub_methods.map((item: Omit<SubMethod, 'visible'>) => ({
      ...item,
      visible: false
    }))
    detectionResult.value.detectionTime = response.timestamps
    exif.value = response.exif
  } catch (error) {
    snackbar.showMessage('获取图片检测结果失败', 'error')
  }
}

const toggleClose = () => {
  showImageDetail.value = false
  llm.value = ''
  llm_image.value = ''
  ela.value = ''
  urn.value = []
  detectionResult.value.detectionTime = ''
  exif.value.detection_time = null
}

const viewImageDetail = (image: Image) => {
  selectedImage.value = image
  showImageDetail.value = true
  fetchImageDetection(image.result_id)
}

// 切换覆盖层显示
const toggleOverlay = (dimension: SubMethod) => {
  // 如果当前点击的是已显示的覆盖层，则关闭它
  if (dimension.visible) {
    dimension.visible = false
    isOverlayVisible.value = false
    activeOverlay.value = null
    return
  }

  // 关闭其他所有覆盖层
  urn.value.forEach(d => {
    if (d !== dimension) {
      d.visible = false
    }
  })

  // 显示当前覆盖层
  dimension.visible = true
  isOverlayVisible.value = true
  activeOverlay.value = dimension.mask_image
}

const getProbabilityColor = (probability: number): string => {
  if (probability > 0.8) return "red"
  if (probability > 0.5) return "orange"
  return "green"
}

const getImageUrl = (url?: string | null) => {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  return `${import.meta.env.VITE_API_URL || ''}${url}`
}

const getSelectedImageUrl = (selectedImage: Image | null) => getImageUrl(selectedImage?.image_url)

const getAvatar = (url?: string | null) => getImageUrl(url)

const selectedFakeCount = computed(() => detectionResult.value.fakeImages.filter(img => img.selected).length)
const selectedRealCount = computed(() => detectionResult.value.realImages.filter(img => img.selected).length)
const isAllFakeSelected = ref(false)
const isAllRealSelected = ref(false)

const selectAllFake = () => {
  const shouldSelect = !isAllFakeSelected.value
  detectionResult.value.fakeImages.forEach(img => img.selected = shouldSelect)
  isAllFakeSelected.value = shouldSelect
}

const selectAllReal = () => {
  const shouldSelect = !isAllRealSelected.value
  detectionResult.value.realImages.forEach(img => img.selected = shouldSelect)
  isAllRealSelected.value = shouldSelect
}

const toggleImageSelection = (image: Image, type: string) => {
  image.selected = !image.selected
  if (type === 'fake') {
    isAllFakeSelected.value = detectionResult.value.fakeImages.length > 0
      && detectionResult.value.fakeImages.every(img => img.selected)
  } else {
    isAllRealSelected.value = detectionResult.value.realImages.length > 0
      && detectionResult.value.realImages.every(img => img.selected)
  }
}

const hasSelectedImages = computed(() => selectedFakeCount.value > 0 || selectedRealCount.value > 0)

// 审核人员相关计算属性
const selectedPeople = computed(() => selectedPeopleList.value.length)
const filteredPeople = computed(() => {
  const people = allPeople.value || []
  if (!searchQuery.value) return people
  const query = searchQuery.value.toLowerCase()
  return people.filter(person => person.username.toLowerCase().includes(query))
})

const searchPeople = async () => {
  if (!searchQuery.value) return
  isSearching.value = true
  try {
    const userStore = useUserStore()
    const response = await publisher.getReviewers({ publisher_id: userStore.id })
    allPeople.value = Array.isArray(response.data?.reviewers) ? response.data.reviewers : []
  } catch (error) {
    console.error('获取审核人员失败:', error)
    snackbar.showMessage('获取审核人员失败', 'error')
    allPeople.value = []
  } finally {
    isSearching.value = false
  }
}

// 监听标签页切换
watch(activeTab, () => {
  // 切换标签页时重置所有造假区域的显示状态
  urn.value.forEach(dimension => {
    dimension.visible = false
  })
  isOverlayVisible.value = false
  activeOverlay.value = null
})
</script>

<style scoped>
.v-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dimension-name {
  min-width: 120px;
}

.dimension-probability {
  min-width: 200px;
}

.v-progress-linear__content {
  font-size: 0.75rem;
}

.overlay-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  mix-blend-mode: multiply;
  opacity: 0.7;
  object-fit: contain;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.detection-summary {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.custom-progress {
  --v-progress-circular-size: 160px;
  --v-progress-circular-underlay-color: v-bind(isDarkMode ? 'rgba(255, 255, 255, 0.05)' : '#f5f5f5');
  transition: all 0.3s ease;
}

.border-r {
  border-right: 1px solid #e5e7eb;
}

.image-grid {
  gap: 16px;
  padding-bottom: 8px;
  min-width: fit-content;
}

.selected-image-card {
  outline: 3px solid rgb(var(--v-theme-primary));
  outline-offset: 3px;
}

.review-config-card {
  scroll-margin-top: 96px;
}

.review-submit-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

@media (max-width: 720px) {
  .review-submit-row {
    grid-template-columns: 1fr;
  }
}

.v-sheet {
  &::-webkit-scrollbar {
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: #555;
  }
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
}

.info-item {
  padding: 8px 12px;
  background-color: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.info-item-dark {
  background-color: rgba(255, 255, 255, 0.05);
}

.responsive-text {
  font-size: clamp(1rem, 2vw, 1.5rem);
}

.text-subtitle-2.responsive-text {
  font-size: clamp(0.75rem, 1.5vw, 1rem);
}

.image-container {
  position: relative;
  width: 100%;
  height: 500px;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
