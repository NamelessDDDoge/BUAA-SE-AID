<template>
  <v-row>
    <v-col cols="12" md="6" class="mb-2">
      <v-select
        v-model="selectedTag"
        :items="mappedTag"
        label="为本批图片添加标签"
        clearable
        variant="outlined"
        hide-details
      />
    </v-col>
    <v-col cols="12" md="6" class="mb-2">
      <v-text-field
        v-model="taskName"
        label="为该检测任务添加名称"
        variant="outlined"
        :rules="[v => !v || v.length <= 30 || '任务名称不能超过 30 个字符']"
        counter="30"
        @update:model-value="handleName"
      />
    </v-col>
  </v-row>

  <v-row>
    <v-col cols="12">
      <div class="d-flex align-center mb-4">
        <span class="text-h6">已提取图片</span>
        <v-spacer />
        <v-btn color="primary" prepend-icon="mdi-check-all" @click="selectAllImages">
          {{ allSelected ? '取消全选' : '全选' }}
        </v-btn>
      </div>
    </v-col>
  </v-row>

  <v-row class="h-100">
    <v-col cols="12" md="4" class="thumbnail-list pa-0">
      <v-card class="h-100">
        <v-card-text class="pa-0 h-100">
          <v-list ref="thumbnailListRef" lines="two" class="thumbnail-scroll h-100">
            <v-list-item
              v-for="(image, index) in displayImages"
              :key="image.image_id"
              :class="{ 'selected-item': image.selected }"
              @click="selectImage(image)"
            >
              <template #prepend>
                <v-avatar size="60" class="me-2">
                  <v-img :src="image.image_url" cover class="bg-grey-lighten-2" />
                </v-avatar>
              </template>
              <v-list-item-title>
                {{ `图片 ${index + 1}` }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ image.extracted_from_pdf ? 'PDF 提取' : '上传图片' }}
              </v-list-item-subtitle>
              <template #append>
                <v-checkbox
                  v-model="image.selected"
                  hide-details
                  density="compact"
                  @click.stop
                  @update:model-value="emitUpdate"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" md="8" class="preview-section pa-0">
      <v-card class="h-100">
        <v-card-text class="pa-0 preview-wrapper h-100">
          <div v-if="selectedImage" class="preview-container h-100">
            <v-btn
              icon="mdi-chevron-left"
              variant="text"
              size="x-large"
              class="preview-nav-btn preview-nav-left"
              :disabled="!canNavigatePrev"
              @click="navigatePrev"
            />

            <div class="image-container">
              <v-img :src="selectedImage.image_url" class="preview-image" contain />
            </div>

            <v-btn
              icon="mdi-chevron-right"
              variant="text"
              size="x-large"
              class="preview-nav-btn preview-nav-right"
              :disabled="!canNavigateNext"
              @click="navigateNext"
            />

            <div class="preview-info pa-4">
              <div class="text-h6">{{ `图片 ${currentIndex + 1}` }}</div>
              <div class="text-body-2">
                {{ selectedImage.extracted_from_pdf ? 'PDF 提取' : '上传图片' }}
              </div>
            </div>
          </div>
          <div v-else class="d-flex align-center justify-center h-100">
            <div class="text-h6 text-grey">请选择一张图片查看详情</div>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useSnackbarStore } from '@/stores/snackbar'
import upload from '@/api/upload'

interface Image {
  image_id: number
  image_url: string
  page_number?: number
  extracted_from_pdf: boolean
  selected: boolean
}

const snackbar = useSnackbarStore()
const taskName = ref('')
const selectedTag = ref<string | null>(null)
const localImages = ref<Image[]>([])
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)
const pageSize = ref(20)
const selectedImage = ref<Image | null>(null)
const currentIndex = ref(-1)
const thumbnailListRef = ref()

const props = withDefaults(defineProps<{
  images?: Image[]
  fileId?: number
}>(), {
  images: () => [],
  fileId: 0,
})

const emit = defineEmits<{
  (e: 'update', selectedImages: Image[]): void
  (e: 'tagChanged', tag: string): void
  (e: 'addName', taskName: string): void
}>()

const displayImages = computed(() => {
  return localImages.value.length > 0 ? localImages.value : props.images
})

const allSelected = computed(() => {
  return displayImages.value.length > 0 && displayImages.value.every(img => img.selected)
})

const canNavigatePrev = computed(() => currentIndex.value > 0)
const canNavigateNext = computed(() => currentIndex.value < displayImages.value.length - 1)

const mappedTag = [
  { title: '医学', value: 'Medicine' },
  { title: '生物', value: 'Biology' },
  { title: '化学', value: 'Chemistry' },
  { title: '图形学', value: 'Graphics' },
  { title: '其他', value: 'Other' },
]

const emitUpdate = () => {
  emit('update', displayImages.value.filter(img => img.selected))
}

const handleName = () => {
  emit('addName', taskName.value)
}

const selectImage = (image: Image) => {
  selectedImage.value = image
  currentIndex.value = displayImages.value.findIndex(img => img.image_id === image.image_id)
}

const navigatePrev = () => {
  if (!canNavigatePrev.value) return
  currentIndex.value -= 1
  selectedImage.value = displayImages.value[currentIndex.value]
}

const navigateNext = () => {
  if (!canNavigateNext.value) return
  currentIndex.value += 1
  selectedImage.value = displayImages.value[currentIndex.value]
}

const selectAllImages = () => {
  const nextValue = !allSelected.value
  displayImages.value.forEach(img => {
    img.selected = nextValue
  })
  emitUpdate()
}

const loadMoreImages = async () => {
  if (loading.value || !hasMore.value || !props.fileId) return

  loading.value = true
  try {
    const response = (await upload.getExtractedImages({
      file_id: props.fileId,
      page_number: page.value,
      page_size: pageSize.value,
    })).data

    const newImages = (response.images || []).map((img: any) => ({
      image_id: img.image_id,
      image_url: `${import.meta.env.VITE_API_URL}${img.image_url}`,
      page_number: img.page_number,
      extracted_from_pdf: img.extracted_from_pdf,
      selected: false,
    }))

    localImages.value.push(...newImages)
    if (!selectedImage.value && localImages.value.length > 0) {
      selectImage(localImages.value[0])
    }

    page.value += 1
    hasMore.value = localImages.value.length < (response.total || 0)
  } catch {
    snackbar.showMessage('图片加载失败', 'error')
  } finally {
    loading.value = false
  }
}

const handleScroll = (event: Event) => {
  const target = event.target as HTMLElement
  if (target.scrollHeight - target.scrollTop - target.clientHeight < 50) {
    loadMoreImages()
  }
}

watch(selectedTag, (newVal) => {
  if (newVal) {
    emit('tagChanged', newVal)
  }
})

onMounted(() => {
  const el = thumbnailListRef.value?.$el ?? thumbnailListRef.value
  el?.addEventListener?.('scroll', handleScroll)
  if (props.fileId) {
    loadMoreImages()
  } else if (displayImages.value.length > 0) {
    selectImage(displayImages.value[0])
  }
})

onUnmounted(() => {
  const el = thumbnailListRef.value?.$el ?? thumbnailListRef.value
  el?.removeEventListener?.('scroll', handleScroll)
})
</script>

<style scoped>
.thumbnail-scroll {
  max-height: 68vh;
  overflow-y: auto;
}

.selected-item {
  background: rgba(var(--v-theme-primary), 0.08);
}

.preview-wrapper {
  min-height: 68vh;
}

.preview-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-container {
  width: 100%;
  height: 100%;
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.preview-image {
  width: 100%;
  height: 100%;
}

.preview-nav-btn {
  position: absolute;
  z-index: 1;
}

.preview-nav-left {
  left: 8px;
}

.preview-nav-right {
  right: 8px;
}

.preview-info {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.45), transparent);
  color: white;
}
</style>
