<template>
  <div v-show="!showProgress">
    <v-row>
      <v-col cols="12" lg="10" class="mx-auto">
        <DetectionTypeSwitcher v-model="detectionType" />

        <ImageTaskForm
          v-if="detectionType === 'image'"
          :files="mainFiles"
          :uploading="uploading"
          :upload-progress="uploadProgress"
          @select="handleMainFiles"
          @remove="removeMainFile"
          @submit="submitUpload"
        />

        <PaperTaskForm
          v-else-if="detectionType === 'paper'"
          :file="mainFiles[0] || null"
          :uploading="uploading"
          :upload-progress="uploadProgress"
          @select="handlePaperFile"
          @clear="clearMainFiles"
          @submit="submitUpload"
        />

        <ReviewTaskForm
          v-else
          :paper-file="reviewPaperFile"
          :review-file="reviewFile"
          :uploading="uploading"
          :upload-progress="uploadProgress"
          @select-paper="handleReviewPaper"
          @select-review="handleReviewFile"
          @clear-paper="clearReviewPaper"
          @clear-review="clearReviewFile"
          @submit="submitUpload"
        />
      </v-col>
    </v-row>
  </div>

  <TaskProgressPanel
    v-show="showProgress"
    :task-type="progressTaskType"
    :file-id="fileId"
    :uploaded-resource-files="uploadedResourceFiles"
    :resource-domain-tag="resourceDomainTag"
    :resource-domain-options="resourceDomainOptions"
    :resource-task-name="resourceTaskName"
    :can-proceed="canProceed"
    :submitting-detection="submittingDetection"
    :paper-enable-image-detection="paperEnableImageDetection"
    :paper-image-detection-supported="paperImageDetectionSupported"
    :paper-image-detection-hint="paperImageDetectionHint"
    :selected-paper-method-count="selectedPaperMethodCount"
    :paper-editable-text="paperEditableText"
    :paper-text-preview-loading="paperTextPreviewLoading"
    :paper-text-preview-error="paperTextPreviewError"
    @back="returnToUpload"
    @update-selected-images="updateSelectedImages"
    @update-tag="handleSelectedTag"
    @update-name="handleName"
    @update:resourceDomainTag="updateResourceDomainTag"
    @update:resourceTaskName="updateResourceTaskName"
    @update:paperEnableImageDetection="updatePaperEnableImageDetection"
    @configure-paper-methods="openPaperMethodSelection"
    @reload-paper-text-preview="reloadPaperTextPreview"
    @update:paperEditableText="updatePaperEditableText"
    @submit-image-task="handleNext"
    @submit-resource-task="handleResourceTaskNext"
  />

  <TaskSelectionDialog
    v-model="taskSelectionDialog"
    :min-selected="taskSelectionMinSelected"
    :confirm-label="taskSelectionConfirmLabel"
    :initial-selection="taskSelectionInitialSelection"
    @confirm="confirmTaskSelection"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import uploadApi from '@/api/upload'
import detectionApi from '@/api/detection'
import resourceTasksApi from '@/api/resourceTasks'
import { useSnackbarStore } from '@/stores/snackbar'
import TaskSelectionDialog from '@/components/steps/TaskSelectionDialog.vue'
import DetectionTypeSwitcher from '@/features/detection/components/DetectionTypeSwitcher.vue'
import ImageTaskForm from '@/features/detection/components/ImageTaskForm.vue'
import PaperTaskForm from '@/features/detection/components/PaperTaskForm.vue'
import ReviewTaskForm from '@/features/detection/components/ReviewTaskForm.vue'
import TaskProgressPanel from '@/features/detection/components/TaskProgressPanel.vue'
import type {
  DetectionType,
  MethodSwitches,
  TaskOption,
  UploadedResourceFile,
} from '@/features/detection/types'
import { createDefaultMethodSwitches } from '@/features/detection/types'

interface Image {
  image_id: number
  image_url: string
  page_number?: number
  extracted_from_pdf: boolean
  selected: boolean
}

interface PendingDetectionPayload {
  image_ids: number[]
  task_name: string
  mode: number
}

type TaskSelectionContext = 'image' | 'paper-image'

const router = useRouter()
const snackbar = useSnackbarStore()

const detectionType = ref<DetectionType>('image')
const mainFiles = ref<File[]>([])
const reviewPaperFile = ref<File | null>(null)
const reviewFile = ref<File | null>(null)

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
const uploadedResourceFiles = ref<UploadedResourceFile[]>([])
const resourceDomainTag = ref('')
const paperEditableText = ref('')
const paperTextPreviewLoading = ref(false)
const paperTextPreviewError = ref('')
const taskSelectionDialog = ref(false)
const pendingDetectionPayload = ref<PendingDetectionPayload | null>(null)
const taskSelectionContext = ref<TaskSelectionContext>('image')
const paperEnableImageDetection = ref(true)
const paperMethodSwitches = ref<MethodSwitches>(createDefaultMethodSwitches())
const taskSelectionMinSelected = computed(() => (taskSelectionContext.value === 'image' ? 1 : 0))
const taskSelectionConfirmLabel = computed(() => (
  taskSelectionContext.value === 'image' ? '确认并提交' : '确认'
))
const taskSelectionInitialSelection = computed(() => (
  taskSelectionContext.value === 'paper-image' ? paperMethodSwitches.value : undefined
))

const MAX_SIZE = 100 * 1024 * 1024
const imageExt = new Set(['png', 'jpg', 'jpeg', 'pdf', 'zip'])
const paperExt = new Set(['docx', 'pdf', 'zip'])
const reviewExt = new Set(['docx', 'pdf', 'txt', 'zip'])

watch(detectionType, () => {
  mainFiles.value = []
  reviewPaperFile.value = null
  reviewFile.value = null
  uploadProgress.value = 0
  paperEnableImageDetection.value = true
  paperMethodSwitches.value = createDefaultMethodSwitches()
})

const resourceDomainOptions: TaskOption[] = [
  { title: '生物', value: 'Biology' },
  { title: '医学', value: 'Medicine' },
  { title: '化学', value: 'Chemistry' },
  { title: '图形学', value: 'Graphics' },
  { title: '其他', value: 'Other' },
]

const paperImageDetectionSupported = computed(() => {
  if (progressTaskType.value !== 'paper') return false
  const fileName = uploadedResourceFiles.value[0]?.name?.toLowerCase() || ''
  return fileName.endsWith('.pdf') || fileName.endsWith('.zip')
})

const paperImageDetectionHint = computed(() => {
  if (!paperImageDetectionSupported.value) {
    return '当前仅支持对 PDF / ZIP 论文提取图像并执行图像检测。'
  }
  return '开启后会复用图像检测链路，仅执行你勾选的图像子任务。'
})

const selectedPaperMethodCount = computed(() => Object.values(paperMethodSwitches.value).filter(Boolean).length)

const getExt = (file: File) => {
  const idx = file.name.lastIndexOf('.')
  return idx === -1 ? '' : file.name.slice(idx + 1).toLowerCase()
}

const validateFile = (file: File, type: DetectionType | 'review-paper' | 'review-file') => {
  if (file.size > MAX_SIZE) {
    return '文件大小超限，单文件不能超过 100MB。'
  }

  const ext = getExt(file)
  if (type === 'image' && !imageExt.has(ext)) {
    return '图像检测仅支持 PNG / JPG / JPEG / PDF / ZIP。'
  }
  if ((type === 'paper' || type === 'review-paper') && !paperExt.has(ext)) {
    return '论文文件仅支持 DOCX / PDF / ZIP。'
  }
  if (type === 'review-file' && !reviewExt.has(ext)) {
    return 'Review 文件仅支持 DOCX / PDF / TXT / ZIP。'
  }
  return null
}

const handleMainFiles = (files: File[]) => {
  const invalid = files.find(file => validateFile(file, detectionType.value))
  if (invalid) {
    snackbar.showMessage(validateFile(invalid, detectionType.value) || '文件格式错误。', 'error')
    return
  }
  mainFiles.value = detectionType.value === 'image' ? files : [files[0]]
}

const handlePaperFile = (file: File) => {
  const error = validateFile(file, 'paper')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  mainFiles.value = [file]
}

const handleReviewPaper = (file: File) => {
  const error = validateFile(file, 'review-paper')
  if (error) {
    snackbar.showMessage(error, 'error')
    return
  }
  reviewPaperFile.value = file
}

const handleReviewFile = (file: File) => {
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

const clearMainFiles = () => {
  mainFiles.value = []
}

const clearReviewPaper = () => {
  reviewPaperFile.value = null
}

const clearReviewFile = () => {
  reviewFile.value = null
}

const updateResourceDomainTag = (value: string) => {
  resourceDomainTag.value = value
}

const updateResourceTaskName = (value: string) => {
  resourceTaskName.value = value
}

const updatePaperEnableImageDetection = (value: boolean) => {
  paperEnableImageDetection.value = value
}

const updatePaperEditableText = (value: string) => {
  paperEditableText.value = value
}

const loadPaperTextPreview = async (resourceFileId: number) => {
  paperTextPreviewLoading.value = true
  paperTextPreviewError.value = ''
  try {
    const response = await uploadApi.getResourceTextPreview(resourceFileId)
    paperEditableText.value = response?.data?.text_content || ''
    if (response?.data?.text_truncated) {
      paperTextPreviewError.value = '提取文本过长，当前为截断预览（前 60000 字）。'
    }
  } catch (error: any) {
    paperEditableText.value = ''
    paperTextPreviewError.value = error?.response?.data?.message || '提取文本预览失败。'
  } finally {
    paperTextPreviewLoading.value = false
  }
}

const reloadPaperTextPreview = async () => {
  const resourceFileId = uploadedResourceFiles.value[0]?.file_id
  if (!resourceFileId) {
    paperTextPreviewError.value = '当前没有可预览的论文文件。'
    return
  }
  await loadPaperTextPreview(resourceFileId)
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
  taskSelectionContext.value = 'image'
  pendingDetectionPayload.value = payload
  taskSelectionDialog.value = true
}

const openPaperMethodSelection = () => {
  taskSelectionContext.value = 'paper-image'
  taskSelectionDialog.value = true
}

const submitDetectionWithSelection = async (methodSwitches: MethodSwitches) => {
  if (!pendingDetectionPayload.value) return

  submittingDetection.value = true
  try {
    await detectionApi.submitDetection({
      ...pendingDetectionPayload.value,
      method_switches: methodSwitches,
    })
    snackbar.showMessage('检测任务提交成功。', 'success')
    pendingDetectionPayload.value = null
    await navigateToHistorySafely()
  } catch (error: any) {
    const message = error?.response?.data?.message || '检测任务提交失败。'
    snackbar.showMessage(message, 'error')
  } finally {
    submittingDetection.value = false
  }
}

const confirmTaskSelection = async (methodSwitches: MethodSwitches) => {
  if (taskSelectionContext.value === 'paper-image') {
    paperMethodSwitches.value = { ...methodSwitches }
    return
  }
  await submitDetectionWithSelection(methodSwitches)
}

const submitUpload = async () => {
  if (uploading.value) return

  try {
    uploading.value = true
    uploadProgress.value = 0

    if (detectionType.value === 'image') {
      if (!mainFiles.value.length) {
        snackbar.showMessage('请先选择图像文件。', 'error')
        return
      }

      if (mainFiles.value.length === 1) {
        const data = await uploadSingleFile(mainFiles.value[0], { detection_type: 'image' })
        progressTaskType.value = 'image'
        fileId.value = data.file_id
        uploadProgress.value = 100
        snackbar.showMessage('图像上传成功，请选择待检测图片。', 'success')
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
        snackbar.showMessage('未提取到可检测图片，请检查上传内容。', 'error')
        return
      }

      uploadProgress.value = 100
      openTaskSelection({
        image_ids: allImageIds,
        task_name: `图像检测 ${new Date().toISOString().slice(0, 19)}`,
        mode: 1,
      })
      return
    }

    if (detectionType.value === 'paper') {
      if (!mainFiles.value.length) {
        snackbar.showMessage('请先选择论文文件。', 'error')
        return
      }

      const data = await uploadSingleFile(mainFiles.value[0], { detection_type: 'paper' })
      progressTaskType.value = 'paper'
      uploadedResourceFiles.value = [{
        file_id: data.file_id,
        name: mainFiles.value[0].name,
        resource_type: 'paper',
      }]
      await loadPaperTextPreview(data.file_id)
      resourceTaskName.value = `论文检测 ${new Date().toISOString().slice(0, 19)}`
      uploadProgress.value = 100
      snackbar.showMessage('论文上传成功，请确认后创建任务。', 'success')
      showProgress.value = true
      return
    }

    if (!reviewPaperFile.value || !reviewFile.value) {
      snackbar.showMessage('Review 检测需要同时上传原论文和 Review 文件。', 'error')
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
    snackbar.showMessage('Review 文件上传成功，请确认后创建任务。', 'success')
    showProgress.value = true
  } catch (error: any) {
    let message = '上传失败，请重试。'
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
    snackbar.showMessage('未找到已上传资源文件，无法创建任务。', 'error')
    return
  }

  if (!resourceDomainTag.value) {
    snackbar.showMessage('请选择学科领域后再创建任务。', 'error')
    return
  }

  const taskType = progressTaskType.value
  if (taskType !== 'paper' && taskType !== 'review') {
    snackbar.showMessage('当前任务类型不支持资源任务创建。', 'error')
    return
  }

  const resourceTypes = new Set(uploadedResourceFiles.value.map(file => file.resource_type))
  if (taskType === 'paper' && ![...resourceTypes].every(type => type === 'paper')) {
    snackbar.showMessage('当前文件组合不满足论文任务要求，请重新选择。', 'error')
    return
  }
  if (taskType === 'review' && !(resourceTypes.has('review_paper') && resourceTypes.has('review_file'))) {
    snackbar.showMessage('当前文件组合不满足 Review 任务要求，请重新选择。', 'error')
    return
  }

  try {
    await Promise.all(
      uploadedResourceFiles.value.map(file => uploadApi.addTag({ fileId: file.file_id, tag: resourceDomainTag.value })),
    )
    const payload: {
      task_type: 'paper' | 'review'
      task_name: string
      file_ids: number[]
      extract_images?: boolean
      if_use_llm?: boolean
      method_switches?: Record<string, boolean>
      text_override?: string
    } = {
      task_type: taskType,
      task_name: resourceTaskName.value,
      file_ids: uploadedResourceFiles.value.map(file => file.file_id),
    }

    if (taskType === 'paper') {
      payload.extract_images = paperImageDetectionSupported.value ? paperEnableImageDetection.value : false
      payload.method_switches = paperEnableImageDetection.value && paperImageDetectionSupported.value
        ? { ...paperMethodSwitches.value }
        : Object.fromEntries(Object.keys(createDefaultMethodSwitches()).map(key => [key, false]))
      payload.if_use_llm = Boolean(payload.method_switches.llm)
      if (paperEditableText.value.trim()) {
        payload.text_override = paperEditableText.value.trim()
      }
    }

    await resourceTasksApi.createResourceTask(payload)
    snackbar.showMessage('任务创建成功。', 'success')
    await navigateToHistorySafely()
  } catch (error: any) {
    const message = error?.response?.data?.message || '任务创建失败。'
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
    console.error('Navigation to history failed after a successful action.', error)
    snackbar.showMessage('任务已创建成功，但跳转检测历史失败，请手动前往检测历史查看。', 'warning')
  }
}

const handleTag = async () => {
  if (!fileId.value || !currentTag.value) return
  try {
    await uploadApi.addTag({ fileId: fileId.value, tag: currentTag.value })
  } catch {
    snackbar.showMessage('标签保存失败。', 'error')
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
  paperEditableText.value = ''
  paperTextPreviewLoading.value = false
  paperTextPreviewError.value = ''
  pendingDetectionPayload.value = null
  taskSelectionDialog.value = false
  taskSelectionContext.value = 'image'
  paperEnableImageDetection.value = true
  paperMethodSwitches.value = createDefaultMethodSwitches()
  mainFiles.value = []
  reviewPaperFile.value = null
  reviewFile.value = null
}
</script>
