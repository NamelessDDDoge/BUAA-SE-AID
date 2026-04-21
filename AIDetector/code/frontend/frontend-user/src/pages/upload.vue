<template>
  <div v-show="!showProgress">
    <v-row>
      <v-col cols="12" lg="10" class="mx-auto">
        <v-card class="mb-6">
          <v-card-title class="text-h6">AI 检测类型</v-card-title>
          <v-card-text>
            <v-btn-toggle v-model="detectionType" mandatory class="d-flex flex-wrap ga-2 type-toggle">
              <v-btn value="image" class="type-btn">学术图像检测</v-btn>
              <v-btn value="paper" class="type-btn">全文论文检测</v-btn>
              <v-btn value="review" class="type-btn">同行评审 Review 检测</v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>

        <v-card>
          <v-card-title class="text-h6">{{ uploadCardTitle }}</v-card-title>
          <v-card-subtitle>{{ uploadCardSubtitle }}</v-card-subtitle>
          <v-card-text>
            <template v-if="detectionType !== 'review'">
              <div
                class="upload-area pa-8"
                @dragover.prevent
                @drop.prevent="onDropMain"
                @click="triggerMainInput"
              >
                <v-icon size="64" color="grey">mdi-cloud-upload</v-icon>
                <div class="text-h6 mt-4">点击或拖拽文件到此处上传</div>
                <div class="text-caption text-grey">{{ formatHint }}</div>
                <input
                  ref="mainInputRef"
                  type="file"
                  style="display: none"
                  :multiple="detectionType === 'image'"
                  :accept="acceptString"
                  @change="onMainSelect"
                >
              </div>

              <v-list v-if="mainFiles.length" class="mt-4" lines="two">
                <v-list-item v-for="(file, idx) in mainFiles" :key="`${file.name}-${idx}`">
                  <template #prepend>
                    <v-icon color="primary">mdi-file</v-icon>
                  </template>
                  <v-list-item-title>{{ file.name }}</v-list-item-title>
                  <v-list-item-subtitle>{{ formatFileSize(file.size) }}</v-list-item-subtitle>
                  <template #append>
                    <v-btn icon="mdi-close" variant="text" @click.stop="removeMainFile(idx)" />
                  </template>
                </v-list-item>
              </v-list>
            </template>

            <template v-else>
              <v-row>
                <v-col cols="12" md="6">
                  <div class="text-subtitle-1 mb-2">1. 上传原论文</div>
                  <div
                    class="upload-area pa-6"
                    @dragover.prevent
                    @drop.prevent="onDropReviewPaper"
                    @click="triggerReviewPaperInput"
                  >
                    <v-icon size="44" color="grey">mdi-file-document-outline</v-icon>
                    <div class="text-body-1 mt-2">点击或拖拽论文文件</div>
                    <div class="text-caption text-grey">支持 DOCX / PDF / ZIP，单文件不超过 100MB</div>
                    <input
                      ref="reviewPaperInputRef"
                      type="file"
                      style="display: none"
                      accept=".docx,.pdf,.zip"
                      @change="onReviewPaperSelect"
                    >
                  </div>

                  <v-card v-if="reviewPaperFile" variant="outlined" class="mt-3">
                    <v-card-text class="d-flex align-center">
                      <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
                      <div class="flex-grow-1">
                        <div class="text-body-2">{{ reviewPaperFile.name }}</div>
                        <div class="text-caption text-grey">{{ formatFileSize(reviewPaperFile.size) }}</div>
                      </div>
                      <v-btn icon="mdi-close" variant="text" @click="reviewPaperFile = null" />
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="12" md="6">
                  <div class="text-subtitle-1 mb-2">2. 上传对应 Review 文件</div>
                  <div
                    class="upload-area pa-6"
                    @dragover.prevent
                    @drop.prevent="onDropReviewFile"
                    @click="triggerReviewFileInput"
                  >
                    <v-icon size="44" color="grey">mdi-comment-text-outline</v-icon>
                    <div class="text-body-1 mt-2">点击或拖拽 Review 文件</div>
                    <div class="text-caption text-grey">支持 DOCX / PDF / TXT / ZIP，单文件不超过 100MB</div>
                    <input
                      ref="reviewFileInputRef"
                      type="file"
                      style="display: none"
                      accept=".docx,.pdf,.txt,.zip"
                      @change="onReviewFileSelect"
                    >
                  </div>

                  <v-card v-if="reviewFile" variant="outlined" class="mt-3">
                    <v-card-text class="d-flex align-center">
                      <v-icon color="primary" class="mr-2">mdi-file-document-edit-outline</v-icon>
                      <div class="flex-grow-1">
                        <div class="text-body-2">{{ reviewFile.name }}</div>
                        <div class="text-caption text-grey">{{ formatFileSize(reviewFile.size) }}</div>
                      </div>
                      <v-btn icon="mdi-close" variant="text" @click="reviewFile = null" />
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </template>

            <v-progress-linear
              v-if="uploading"
              class="mt-6"
              :model-value="uploadProgress"
              height="18"
              color="primary"
              rounded
            >
              <template #default>
                <span class="text-caption text-white">上传中 {{ Math.round(uploadProgress) }}%</span>
              </template>
            </v-progress-linear>
          </v-card-text>

          <v-card-actions class="px-6 pb-6">
            <v-spacer />
            <v-btn color="primary" size="large" :loading="uploading" @click="submitUpload">
              提交上传
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>

  <div v-show="showProgress" class="upload-progress">
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" class="mr-2 return-btn" @click="returnToUpload">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回上传</span>
    </div>

    <v-card>
      <v-card-text v-if="progressTaskType === 'image'">
        <ImageSelectionStep
          v-if="fileId"
          :file-id="fileId"
          @update="updateSelectedImages"
          @tag-changed="handleSelectedTag"
          @add-name="handleName"
        />
      </v-card-text>
      <v-card-actions v-if="progressTaskType === 'image'">
        <v-spacer />
        <v-btn
          color="primary"
          variant="elevated"
          append-icon="mdi-arrow-right"
          :disabled="!canProceed"
          :loading="submittingDetection"
          @click="handleNext"
        >
          提交检测
        </v-btn>
      </v-card-actions>

      <template v-else>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            上传完成，请确认任务信息后创建检测任务。
          </v-alert>

          <v-list lines="two" class="mb-4">
            <v-list-item v-for="item in uploadedResourceFiles" :key="item.file_id">
              <template #prepend>
                <v-icon color="primary">mdi-file-document-outline</v-icon>
              </template>
              <v-list-item-title>{{ item.name }}</v-list-item-title>
              <v-list-item-subtitle>资源类型：{{ item.resource_type }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <v-select
            v-model="resourceDomainTag"
            :items="resourceDomainOptions"
            item-title="title"
            item-value="value"
            label="学科领域"
            placeholder="请选择学科领域"
            variant="outlined"
            density="comfortable"
            class="mb-4"
          />

          <v-text-field
            v-model="resourceTaskName"
            label="任务名称"
            placeholder="请输入任务名称"
            variant="outlined"
            density="comfortable"
            maxlength="64"
            counter
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="elevated" append-icon="mdi-arrow-right" @click="handleResourceTaskNext">
            创建任务
          </v-btn>
        </v-card-actions>
      </template>
    </v-card>
  </div>

  <TaskSelectionDialog
    v-model="taskSelectionDialog"
    @confirm="confirmTaskSelection"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import uploadApi from '@/api/upload'
import publisher from '@/api/publisher'
import { useSnackbarStore } from '@/stores/snackbar'
import ImageSelectionStep from '@/components/steps/ImageSelectionStep.vue'
import TaskSelectionDialog from '@/components/steps/TaskSelectionDialog.vue'

type DetectionType = 'image' | 'paper' | 'review'

interface Image {
  image_id: number
  image_url: string
  page_number?: number
  extracted_from_pdf: boolean
  selected: boolean
}

type MethodSwitches = {
  llm: boolean
  ela: boolean
  exif: boolean
  cmd: boolean
  urn_coarse_v2: boolean
  urn_blurring: boolean
  urn_brute_force: boolean
  urn_contrast: boolean
  urn_inpainting: boolean
}

interface PendingDetectionPayload {
  image_ids: number[]
  task_name: string
  mode: number
}

const router = useRouter()
const snackbar = useSnackbarStore()

const detectionType = ref<DetectionType>('image')
const mainFiles = ref<File[]>([])
const reviewPaperFile = ref<File | null>(null)
const reviewFile = ref<File | null>(null)

const mainInputRef = ref<HTMLInputElement | null>(null)
const reviewPaperInputRef = ref<HTMLInputElement | null>(null)
const reviewFileInputRef = ref<HTMLInputElement | null>(null)

const uploading = ref(false)
const submittingDetection = ref(false)
const uploadProgress = ref(0)
const showProgress = ref(false)
const progressTaskType = ref<DetectionType>('image')
const fileId = ref<number | null>(null)
const selectedImages = ref<Image[]>([])
const currentTag = ref('')
const currentTaskName = ref('')
const resourceTaskName = ref('')
const uploadedResourceFiles = ref<Array<{ file_id: number; name: string; resource_type: string }>>([])
const resourceDomainTag = ref('')
const taskSelectionDialog = ref(false)
const pendingDetectionPayload = ref<PendingDetectionPayload | null>(null)

const MAX_SIZE = 100 * 1024 * 1024
const imageExt = new Set(['png', 'jpg', 'jpeg', 'pdf', 'zip'])
const paperExt = new Set(['docx', 'pdf', 'zip'])
const reviewExt = new Set(['docx', 'pdf', 'txt', 'zip'])

watch(detectionType, () => {
  mainFiles.value = []
  reviewPaperFile.value = null
  reviewFile.value = null
  uploadProgress.value = 0
})

const uploadCardTitle = computed(() => {
  if (detectionType.value === 'image') return '学术图像上传'
  if (detectionType.value === 'paper') return '全文论文上传'
  return 'Review 检测上传（原论文 + Review）'
})

const uploadCardSubtitle = computed(() => {
  if (detectionType.value === 'image') {
    return '支持 PNG / JPG / JPEG / ZIP，可上传单张或多张图片。'
  }
  if (detectionType.value === 'paper') {
    return '支持 DOCX / PDF / ZIP，用于全文论文 AIGC 检测。'
  }
  return '请先上传原论文，再上传对应 Review 文件，二者校验通过后才允许创建任务。'
})

const formatHint = computed(() => {
  if (detectionType.value === 'image') {
    return '支持 PNG / JPG / JPEG / ZIP，单文件不超过 100MB。'
  }
  return '支持 DOCX / PDF / ZIP，单文件不超过 100MB。'
})

const acceptString = computed(() => (
  detectionType.value === 'image' ? '.png,.jpg,.jpeg,.pdf,.zip' : '.docx,.pdf,.zip'
))

const resourceDomainOptions = [
  { title: '生物', value: 'Biology' },
  { title: '医学', value: 'Medicine' },
  { title: '化学', value: 'Chemistry' },
  { title: '图形学', value: 'Graphics' },
  { title: '其他', value: 'Other' },
]

const triggerMainInput = () => mainInputRef.value?.click()
const triggerReviewPaperInput = () => reviewPaperInputRef.value?.click()
const triggerReviewFileInput = () => reviewFileInputRef.value?.click()

const getExt = (file: File) => {
  const idx = file.name.lastIndexOf('.')
  return idx === -1 ? '' : file.name.slice(idx + 1).toLowerCase()
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

const validateFile = (file: File, type: DetectionType | 'review-paper' | 'review-file') => {
  if (file.size > MAX_SIZE) {
    return '文件大小超限，单文件不能超过 100MB'
  }

  const ext = getExt(file)
  if (type === 'image' && !imageExt.has(ext)) {
    return '图像检测仅支持 PNG / JPG / JPEG / ZIP'
  }
  if ((type === 'paper' || type === 'review-paper') && !paperExt.has(ext)) {
    return '论文文件仅支持 DOCX / PDF / ZIP'
  }
  if (type === 'review-file' && !reviewExt.has(ext)) {
    return 'Review 文件仅支持 DOCX / PDF / TXT / ZIP'
  }
  return null
}

const onMainSelect = (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (!files.length) return
  const invalid = files.find(file => validateFile(file, detectionType.value))
  if (invalid) {
    snackbar.showMessage(validateFile(invalid, detectionType.value) || '文件格式错误', 'error')
    return
  }
  mainFiles.value = detectionType.value === 'image' ? files : [files[0]]
}

const onReviewPaperSelect = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const error = validateFile(file, 'review-paper')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  reviewPaperFile.value = file
}

const onReviewFileSelect = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const error = validateFile(file, 'review-file')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  reviewFile.value = file
}

const onDropMain = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files || [])
  if (!files.length) return
  const invalid = files.find(file => validateFile(file, detectionType.value))
  if (invalid) {
    snackbar.showMessage(validateFile(invalid, detectionType.value) || '文件格式错误', 'error')
    return
  }
  mainFiles.value = detectionType.value === 'image' ? files : [files[0]]
}

const onDropReviewPaper = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  const error = validateFile(file, 'review-paper')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  reviewPaperFile.value = file
}

const onDropReviewFile = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  const error = validateFile(file, 'review-file')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  reviewFile.value = file
}

const removeMainFile = (idx: number) => {
  mainFiles.value.splice(idx, 1)
}

const uploadSingleFile = async (
  file: File,
  payload: {
    detection_type: DetectionType
    review_role?: 'paper' | 'review'
    linked_paper_file_id?: number
  },
  progressBase = 0,
  progressSpan = 100,
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('detection_type', payload.detection_type)
  if (payload.review_role) formData.append('review_role', payload.review_role)
  if (payload.linked_paper_file_id) {
    formData.append('linked_paper_file_id', String(payload.linked_paper_file_id))
  }

  const response = await uploadApi.uploadFile(formData, (event: ProgressEvent) => {
    const total = event.total || file.size || 1
    const percent = Math.min(100, (event.loaded / total) * 100)
    uploadProgress.value = progressBase + (percent * progressSpan) / 100
  })

  return response.data
}

const openTaskSelection = (payload: PendingDetectionPayload) => {
  pendingDetectionPayload.value = payload
  taskSelectionDialog.value = true
}

const submitDetectionWithSelection = async (methodSwitches: MethodSwitches) => {
  if (!pendingDetectionPayload.value) return

  submittingDetection.value = true
  try {
    await publisher.submitDetection({
      ...pendingDetectionPayload.value,
      method_switches: methodSwitches,
    })
    snackbar.showMessage('检测任务提交成功', 'success')
    pendingDetectionPayload.value = null
    await navigateToHistorySafely()
  } catch (error: any) {
    const message = error?.response?.data?.message || '检测任务提交失败'
    snackbar.showMessage(message, 'error')
  } finally {
    submittingDetection.value = false
  }
}

const confirmTaskSelection = async (methodSwitches: MethodSwitches) => {
  await submitDetectionWithSelection(methodSwitches)
}

const submitUpload = async () => {
  if (uploading.value) return

  try {
    uploading.value = true
    uploadProgress.value = 0

    if (detectionType.value === 'image') {
      if (!mainFiles.value.length) {
        snackbar.showMessage('请先选择图像文件', 'error')
        return
      }

      if (mainFiles.value.length === 1) {
        const data = await uploadSingleFile(mainFiles.value[0], { detection_type: 'image' })
        progressTaskType.value = 'image'
        fileId.value = data.file_id
        uploadProgress.value = 100
        snackbar.showMessage('图像上传成功，请选择待检测图片', 'success')
        showProgress.value = true
        return
      }

      const allImageIds: number[] = []
      for (let i = 0; i < mainFiles.value.length; i += 1) {
        const file = mainFiles.value[i]
        const data = await uploadSingleFile(
          file,
          { detection_type: 'image' },
          (i / mainFiles.value.length) * 80,
          80 / mainFiles.value.length,
        )

        const extracted = await uploadApi.getExtractedImages({
          file_id: data.file_id,
          page_number: 1,
          page_size: 1000,
        })
        const ids = (extracted.data?.images || []).map((img: any) => img.image_id)
        allImageIds.push(...ids)
      }

      if (!allImageIds.length) {
        snackbar.showMessage('未提取到可检测图片，请检查上传内容', 'error')
        return
      }

      uploadProgress.value = 100
      openTaskSelection({
        image_ids: allImageIds,
        task_name: `批量图像检测 ${new Date().toISOString().slice(0, 19)}`,
        mode: 1,
      })
      return
    }

    if (detectionType.value === 'paper') {
      if (!mainFiles.value.length) {
        snackbar.showMessage('请先选择论文文件', 'error')
        return
      }

      const data = await uploadSingleFile(mainFiles.value[0], { detection_type: 'paper' })
      progressTaskType.value = 'paper'
      uploadedResourceFiles.value = [{
        file_id: data.file_id,
        name: mainFiles.value[0].name,
        resource_type: 'paper',
      }]
      resourceTaskName.value = `论文检测 ${new Date().toISOString().slice(0, 19)}`
      uploadProgress.value = 100
      snackbar.showMessage('论文上传成功，请确认后创建任务', 'success')
      showProgress.value = true
      return
    }

    if (!reviewPaperFile.value || !reviewFile.value) {
      snackbar.showMessage('Review 检测需要同时上传原论文和 Review 文件', 'error')
      return
    }

    const paperData = await uploadSingleFile(
      reviewPaperFile.value,
      { detection_type: 'review', review_role: 'paper' },
      0,
      50,
    )

    const reviewData = await uploadSingleFile(
      reviewFile.value,
      {
        detection_type: 'review',
        review_role: 'review',
        linked_paper_file_id: paperData.file_id,
      },
      50,
      50,
    )

    progressTaskType.value = 'review'
    uploadedResourceFiles.value = [
      { file_id: paperData.file_id, name: reviewPaperFile.value.name, resource_type: 'review_paper' },
      { file_id: reviewData.file_id, name: reviewFile.value.name, resource_type: 'review_file' },
    ]
    resourceTaskName.value = `Review 检测 ${new Date().toISOString().slice(0, 19)}`
    uploadProgress.value = 100
    snackbar.showMessage('Review 文件上传成功，请确认后创建任务', 'success')
    showProgress.value = true
  } catch (error: any) {
    let message = '上传失败，请重试'
    if (axios.isAxiosError(error)) {
      message = error.response?.data?.message || message
    }
    snackbar.showMessage(message, 'error')
  } finally {
    uploading.value = false
  }
}

const handleResourceTaskNext = async () => {
  if (!uploadedResourceFiles.value.length) {
    snackbar.showMessage('未找到已上传资源文件，无法创建任务', 'error')
    return
  }

  if (!resourceDomainTag.value) {
    snackbar.showMessage('请选择学科领域后再创建任务', 'error')
    return
  }

  const taskType = progressTaskType.value
  if (taskType !== 'paper' && taskType !== 'review') {
    snackbar.showMessage('当前任务类型不支持资源任务创建', 'error')
    return
  }

  const resourceTypes = new Set(uploadedResourceFiles.value.map(file => file.resource_type))
  if (taskType === 'paper' && ![...resourceTypes].every(type => type === 'paper')) {
    snackbar.showMessage('当前文件组合不满足论文任务要求，请重新选择', 'error')
    return
  }
  if (taskType === 'review' && !(resourceTypes.has('review_paper') && resourceTypes.has('review_file'))) {
    snackbar.showMessage('当前文件组合不满足 Review 任务要求，请重新选择', 'error')
    return
  }

  try {
    await Promise.all(
      uploadedResourceFiles.value.map(file => uploadApi.addTag({ fileId: file.file_id, tag: resourceDomainTag.value })),
    )
    await publisher.createResourceTask({
      task_type: taskType,
      task_name: resourceTaskName.value,
      file_ids: uploadedResourceFiles.value.map(file => file.file_id),
    })
    snackbar.showMessage('任务创建成功', 'success')
    await navigateToHistorySafely()
  } catch (error: any) {
    const message = error?.response?.data?.message || '任务创建失败'
    snackbar.showMessage(message, 'error')
  }
}

const canProceed = computed(() => (
  selectedImages.value.length > 0 && (!currentTaskName.value || currentTaskName.value.length <= 30)
))

const updateSelectedImages = (images: Image[]) => {
  selectedImages.value = images
}

const handleSelectedTag = (newTag: string) => {
  currentTag.value = newTag
}

const handleName = (newName: string) => {
  currentTaskName.value = newName
}

const navigateToHistorySafely = async () => {
  try {
    await router.push('/history')
  } catch (error) {
    console.error('Navigation to history failed after successful task action.', error)
    snackbar.showMessage('任务已创建成功，但跳转到历史页面失败，请手动前往检测历史查看', 'warning')
  }
}

const handleTag = async () => {
  if (!fileId.value || !currentTag.value) return
  try {
    await uploadApi.addTag({ fileId: fileId.value, tag: currentTag.value })
  } catch {
    snackbar.showMessage('标签保存失败', 'error')
  }
}

const handleNext = async () => {
  if (!canProceed.value) return
  await handleTag()
  openTaskSelection({
    image_ids: selectedImages.value.map(img => img.image_id),
    task_name: currentTaskName.value || `图像检测 ${new Date().toISOString().slice(0, 19)}`,
    mode: 1,
  })
}

const returnToUpload = () => {
  showProgress.value = false
  progressTaskType.value = 'image'
  fileId.value = null
  selectedImages.value = []
  currentTag.value = ''
  currentTaskName.value = ''
  resourceTaskName.value = ''
  resourceDomainTag.value = ''
  uploadedResourceFiles.value = []
  pendingDetectionPayload.value = null
  taskSelectionDialog.value = false
  mainFiles.value = []
  reviewPaperFile.value = null
  reviewFile.value = null
}
</script>

<style scoped>
.type-toggle {
  width: 100%;
}

.type-btn {
  flex: 1 1 220px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.upload-area:hover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.upload-progress {
  position: relative;
  min-height: 100vh;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}
</style>
