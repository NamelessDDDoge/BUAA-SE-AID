<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">资源管理</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">
          统一管理图像、论文和评审资源，支持查看详情、下载文件和删除任务。
        </div>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="keyword"
          prepend-inner-icon="mdi-magnify"
          label="搜索资源名称"
          variant="outlined"
          hide-details
          clearable
        />
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12">
        <TaskTypeFilter v-model="taskTypeFilter" :options="taskTypeOptions" />
      </v-col>
    </v-row>

    <v-row class="mb-6">
      <v-col cols="12" md="4">
        <v-card rounded="lg" elevation="2" class="stat-card">
          <div class="text-overline">资源总数</div>
          <div class="text-h4 font-weight-bold">{{ summary.total_task_count }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" elevation="2" class="stat-card">
          <div class="text-overline">已完成资源</div>
          <div class="text-h4 font-weight-bold">{{ summary.completed_task_count }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" elevation="2" class="stat-card">
          <div class="text-overline">近 30 天新增</div>
          <div class="text-h4 font-weight-bold">{{ summary.recent_task_count }}</div>
        </v-card>
      </v-col>
    </v-row>

    <v-card elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center flex-wrap ga-2">
        <span class="text-h6">{{ tableTitle }}</span>
        <v-spacer />
        <span class="text-caption text-medium-emphasis">共 {{ totalTasks }} 条记录</span>
      </v-card-title>

      <v-data-table :headers="headers" :items="tasks" :loading="loading" hide-default-footer>
        <template #item.task_type="{ item }">
          <v-chip size="small" :color="taskTypeColor(item.task_type)" variant="tonal">
            {{ taskTypeLabel(item.task_type) }}
          </v-chip>
        </template>

        <template #item.status="{ item }">
          <v-chip size="small" :color="statusColor(item.status)">
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex ga-2 justify-center">
            <v-btn size="small" variant="tonal" color="primary" @click="openDetail(item)">查看详情</v-btn>
            <v-btn size="small" variant="tonal" color="error" @click="openDeleteDialog(item)">删除</v-btn>
          </div>
        </template>

        <template #no-data>
          <div class="py-8 text-center text-medium-emphasis">暂无资源数据</div>
        </template>
      </v-data-table>
    </v-card>

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

    <v-dialog v-model="detailDialog" fullscreen scrollable>
      <v-card>
        <v-toolbar color="surface" density="comfortable">
          <v-btn icon="mdi-close" @click="closeDetail"></v-btn>
          <v-toolbar-title>{{ detailDialogTitle }}</v-toolbar-title>
          <v-spacer />
          <v-btn v-if="selectedTaskDetail?.report_file_url" color="primary" variant="text" @click="openLink(selectedTaskDetail.report_file_url)">
            下载报告
          </v-btn>
          <v-btn color="error" variant="text" :loading="deleteLoading" @click="openDeleteDialog(selectedTaskSummary)">
            删除资源
          </v-btn>
        </v-toolbar>

        <v-card-text class="detail-shell">
          <div v-if="detailLoading" class="py-12 text-center">
            <v-progress-circular color="primary" indeterminate size="42" />
            <div class="text-body-2 text-medium-emphasis mt-4">正在加载资源详情...</div>
          </div>

          <template v-else-if="selectedTaskSummary && selectedTaskDetail">
            <v-row class="mb-4">
              <v-col cols="12" md="8">
                <div class="text-h5 font-weight-bold">{{ selectedTaskSummary.task_name }}</div>
                <div class="text-body-2 text-medium-emphasis mt-2">{{ selectedTaskDetail.result_summary || selectedTaskSummary.result_summary || '暂无摘要' }}</div>
              </v-col>
              <v-col cols="12" md="4" class="d-flex justify-md-end align-start">
                <v-chip :color="statusColor(selectedTaskSummary.status)" class="mr-2">{{ statusLabel(selectedTaskSummary.status) }}</v-chip>
                <v-chip :color="taskTypeColor(selectedTaskSummary.task_type)" variant="tonal">{{ taskTypeLabel(selectedTaskSummary.task_type) }}</v-chip>
              </v-col>
            </v-row>

            <v-row class="mb-6">
              <v-col v-for="item in overviewItems" :key="item.label" cols="12" sm="6" md="3">
                <v-card rounded="lg" elevation="1" class="overview-card">
                  <div class="text-caption text-medium-emphasis">{{ item.label }}</div>
                  <div class="text-body-1 font-weight-medium mt-2">{{ item.value }}</div>
                </v-card>
              </v-col>
            </v-row>

            <v-card v-if="selectedTaskSummary.task_type === 'image'" rounded="lg" elevation="1" class="mb-6">
              <v-card-title>图像详情与检测结果</v-card-title>
              <v-card-text>
                <v-row class="mb-4">
                  <v-col cols="12" md="4">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">图像总数</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ imageResultSummary.total_images }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">疑似造假图像</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ imageResultSummary.fake_images }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">已完成检测</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ imageResultSummary.completed_images }}</div>
                    </v-card>
                  </v-col>
                </v-row>

                <v-row v-if="imageResults.length">
                  <v-col v-for="result in imageResults" :key="result.result_id" cols="12" md="6" lg="4">
                    <v-card rounded="lg" variant="outlined" class="fill-height">
                      <v-img v-if="getImagePreviewUrl(result)" :src="getImagePreviewUrl(result) || undefined" height="220" cover />
                      <v-card-text>
                        <div class="text-subtitle-1 font-weight-medium">图像 {{ result.image_id }}</div>
                        <div class="text-body-2 text-medium-emphasis mt-2">页码：{{ result.page_number ?? '-' }}</div>
                        <div class="text-body-2 text-medium-emphasis">检测状态：{{ statusLabel(result.status) }}</div>
                        <div class="text-body-2 text-medium-emphasis">检测结论：{{ result.is_fake ? '疑似造假' : '真实' }}</div>
                        <div class="text-body-2 text-medium-emphasis">置信度：{{ formatConfidence(result.confidence_score) }}</div>
                        <div class="text-body-2 text-medium-emphasis">检测时间：{{ formatDate(result.detection_time) }}</div>
                        <div class="d-flex ga-2 mt-4">
                          <v-btn v-if="resolveAssetUrl(result.image_url)" size="small" color="primary" variant="tonal" @click="openResolvedLink(resolveAssetUrl(result.image_url))">查看图像</v-btn>
                          <v-btn v-if="resolveAssetUrl(result.image_url)" size="small" variant="text" @click="openResolvedLink(resolveAssetUrl(result.image_url))">下载图像</v-btn>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
                <div v-else class="text-body-2 text-medium-emphasis">暂无图像检测结果。</div>
              </v-card-text>
            </v-card>

            <v-card v-if="selectedTaskSummary.task_type === 'paper'" rounded="lg" elevation="1" class="mb-6">
              <v-card-title>论文检测摘要</v-card-title>
              <v-card-text>
                <v-row class="mb-4">
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">疑似段落</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ paperSuspiciousCount }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">基本确认 AI</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ paperConfirmedCount }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">参考文献检查</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ paperReferenceCount }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">图片检测数</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ paperImageResultCount }}</div>
                    </v-card>
                  </v-col>
                </v-row>

                <div class="d-flex ga-2 mb-4 flex-wrap">
                  <v-btn
                    v-if="primaryPaperFile"
                    :disabled="!primaryPaperFile.file_available || !primaryPaperFile.download_url"
                    color="primary"
                    variant="tonal"
                    @click="openResourceFile(primaryPaperFile)"
                  >
                    下载论文原文
                  </v-btn>
                  <v-btn v-if="selectedTaskDetail.report_file_url" variant="text" @click="openLink(selectedTaskDetail.report_file_url)">下载检测报告</v-btn>
                </div>

                <div v-if="primaryPaperFile?.download_message" class="text-body-2 text-warning mb-4">{{ primaryPaperFile.download_message }}</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <v-card rounded="lg" variant="outlined" class="fill-height">
                      <v-card-title class="text-subtitle-1">疑似段落</v-card-title>
                      <v-card-text>
                        <v-list lines="three" density="compact" v-if="paperSuspiciousParagraphs.length">
                          <v-list-item v-for="item in paperSuspiciousParagraphs.slice(0, 5)" :key="`suspicious-${item.paragraph_index}`">
                            <template #title>第 {{ item.paragraph_index }} 段</template>
                            <template #subtitle>{{ item.explanation || '无说明' }}</template>
                          </v-list-item>
                        </v-list>
                        <div v-else class="text-body-2 text-medium-emphasis">暂无疑似段落。</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card rounded="lg" variant="outlined" class="fill-height">
                      <v-card-title class="text-subtitle-1">基本确认 AI 段落</v-card-title>
                      <v-card-text>
                        <v-list lines="three" density="compact" v-if="paperConfirmedParagraphs.length">
                          <v-list-item v-for="item in paperConfirmedParagraphs.slice(0, 5)" :key="`confirmed-${item.paragraph_index}`">
                            <template #title>第 {{ item.paragraph_index }} 段</template>
                            <template #subtitle>{{ item.reason || '无说明' }}</template>
                          </v-list-item>
                        </v-list>
                        <div v-else class="text-body-2 text-medium-emphasis">暂无基本确认 AI 段落。</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <v-card v-if="selectedTaskSummary.task_type === 'review'" rounded="lg" elevation="1" class="mb-6">
              <v-card-title>评审检测摘要</v-card-title>
              <v-card-text>
                <v-row class="mb-4">
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">模板化等级</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ reviewOverall.template_like_level || '-' }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">相关度等级</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ reviewOverall.relevance_level || '-' }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">可疑段落数</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ reviewSuspiciousCount }}</div>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="3">
                    <v-card rounded="lg" class="summary-card" elevation="0">
                      <div class="text-caption text-medium-emphasis">相关性结果数</div>
                      <div class="text-h5 font-weight-bold mt-2">{{ reviewRelevanceCount }}</div>
                    </v-card>
                  </v-col>
                </v-row>

                <div class="d-flex ga-2 mb-4 flex-wrap">
                  <v-btn
                    v-if="reviewFile"
                    :disabled="!reviewFile.file_available || !reviewFile.download_url"
                    color="primary"
                    variant="tonal"
                    @click="openResourceFile(reviewFile)"
                  >
                    下载 Review 原文
                  </v-btn>
                  <v-btn
                    v-if="originalPaperFile"
                    :disabled="!originalPaperFile.file_available || !originalPaperFile.download_url"
                    variant="tonal"
                    color="secondary"
                    @click="openResourceFile(originalPaperFile)"
                  >
                    下载原论文
                  </v-btn>
                </div>

                <div v-if="reviewFile?.download_message" class="text-body-2 text-warning mb-2">{{ reviewFile.download_message }}</div>
                <div v-if="originalPaperFile?.download_message" class="text-body-2 text-warning mb-4">{{ originalPaperFile.download_message }}</div>

                <v-row>
                  <v-col cols="12" md="6">
                    <v-card rounded="lg" variant="outlined" class="fill-height">
                      <v-card-title class="text-subtitle-1">可疑段落</v-card-title>
                      <v-card-text>
                        <v-list lines="three" density="compact" v-if="reviewSuspiciousParagraphs.length">
                          <v-list-item v-for="item in reviewSuspiciousParagraphs.slice(0, 5)" :key="`review-suspicious-${item.paragraph_index}`">
                            <template #title>第 {{ item.paragraph_index }} 段</template>
                            <template #subtitle>{{ item.explanation || '无说明' }}</template>
                          </v-list-item>
                        </v-list>
                        <div v-else class="text-body-2 text-medium-emphasis">暂无可疑段落。</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-card rounded="lg" variant="outlined" class="fill-height">
                      <v-card-title class="text-subtitle-1">相关性结果</v-card-title>
                      <v-card-text>
                        <v-list lines="three" density="compact" v-if="reviewRelevanceResults.length">
                          <v-list-item v-for="item in reviewRelevanceResults.slice(0, 5)" :key="`review-relevance-${item.review_paragraph_index}`">
                            <template #title>评审段落 {{ item.review_paragraph_index }}</template>
                            <template #subtitle>
                              相关度：{{ item.label || '-' }} / 分数：{{ formatConfidence(item.relevance_score) }}
                            </template>
                          </v-list-item>
                        </v-list>
                        <div v-else class="text-body-2 text-medium-emphasis">暂无相关性结果。</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </template>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="420">
      <v-card>
        <v-card-title class="text-h6">确认删除资源</v-card-title>
        <v-card-text>
          确认删除“{{ selectedTaskSummary?.task_name || '当前资源' }}”吗？删除后任务及其检测产物将一并移除。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleteLoading" @click="handleDelete">确认删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import tasksApi from '@/api/tasks'
import TaskTypeFilter from '@/features/tasks/TaskTypeFilter.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const loading = ref(false)
const detailLoading = ref(false)
const deleteLoading = ref(false)
const detailDialog = ref(false)
const deleteDialog = ref(false)
const keyword = ref('')
const taskTypeFilter = ref('all')
const pageSize = ref(10)
const currentPage = ref(1)
const totalPages = ref(1)
const totalTasks = ref(0)
const tasks = ref<any[]>([])
const selectedTaskSummary = ref<any | null>(null)
const selectedTaskDetail = ref<any | null>(null)

const summary = ref({
  total_task_count: 0,
  completed_task_count: 0,
  recent_task_count: 0,
  task_type_counts: {
    image: 0,
    paper: 0,
    review: 0,
  },
})

const resourceTypeTextMap: Record<string, string> = {
  image: '图像',
  paper: '论文',
  review: '评审',
}

const taskTypeOptions = computed(() => [
  { label: '全部', value: 'all', color: 'grey', count: summary.value.total_task_count },
  { label: '图像', value: 'image', color: 'primary', count: summary.value.task_type_counts.image },
  { label: '论文', value: 'paper', color: 'deep-orange', count: summary.value.task_type_counts.paper },
  { label: '评审', value: 'review', color: 'teal', count: summary.value.task_type_counts.review },
])

const currentResourceLabel = computed(() => {
  if (taskTypeFilter.value === 'all') return '资源'
  return resourceTypeTextMap[taskTypeFilter.value] || '资源'
})

const tableTitle = computed(() => {
  if (taskTypeFilter.value === 'all') return '全部资源列表'
  return `${currentResourceLabel.value}列表`
})

const headers = computed(() => [
  { title: `${currentResourceLabel.value}ID`, key: 'task_id', align: 'center' as const },
  { title: `${currentResourceLabel.value}名称`, key: 'task_name', align: 'start' as const },
  { title: '资源类型', key: 'task_type', align: 'center' as const },
  { title: '状态', key: 'status', align: 'center' as const },
  { title: '发布者', key: 'username', align: 'start' as const },
  { title: '所属组织', key: 'organization', align: 'start' as const },
  { title: '上传时间', key: 'upload_time', align: 'center' as const },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false },
])

const detailDialogTitle = computed(() => {
  if (!selectedTaskSummary.value) return '资源详情'
  return `${taskTypeLabel(selectedTaskSummary.value.task_type)}详情`
})

const overviewItems = computed(() => {
  if (!selectedTaskSummary.value || !selectedTaskDetail.value) return []

  return [
    { label: `${taskTypeLabel(selectedTaskSummary.value.task_type)}ID`, value: selectedTaskSummary.value.task_id },
    { label: `${taskTypeLabel(selectedTaskSummary.value.task_type)}名称`, value: selectedTaskSummary.value.task_name || '-' },
    { label: '资源类型', value: taskTypeLabel(selectedTaskSummary.value.task_type) },
    { label: '状态', value: statusLabel(selectedTaskSummary.value.status) },
    { label: '发布者', value: selectedTaskSummary.value.username || '-' },
    { label: '所属组织', value: selectedTaskSummary.value.organization || '-' },
    { label: '上传时间', value: formatDate(selectedTaskSummary.value.upload_time) },
    { label: '完成时间', value: formatDate(selectedTaskDetail.value.completion_time) },
  ]
})

const resourceFiles = computed(() => selectedTaskDetail.value?.resource_files || [])
const imageResults = computed(() => selectedTaskDetail.value?.results?.image_results || [])
const imageResultSummary = computed(() => selectedTaskDetail.value?.results?.summary || { total_images: 0, fake_images: 0, completed_images: 0 })
const paperResults = computed(() => selectedTaskDetail.value?.results || {})
const reviewResults = computed(() => selectedTaskDetail.value?.results || {})
const paperSuspiciousParagraphs = computed(() => paperResults.value.suspicious_paragraphs || [])
const paperConfirmedParagraphs = computed(() => paperResults.value.confirmed_ai_paragraphs || [])
const paperSuspiciousCount = computed(() => paperSuspiciousParagraphs.value.length)
const paperConfirmedCount = computed(() => paperConfirmedParagraphs.value.length)
const paperReferenceCount = computed(() => (paperResults.value.reference_results || []).length)
const paperImageResultCount = computed(() => (paperResults.value.image_results || []).length)
const reviewSuspiciousParagraphs = computed(() => reviewResults.value.suspicious_paragraphs || [])
const reviewRelevanceResults = computed(() => reviewResults.value.relevance_results || [])
const reviewSuspiciousCount = computed(() => reviewSuspiciousParagraphs.value.length)
const reviewRelevanceCount = computed(() => reviewRelevanceResults.value.length)
const reviewOverall = computed(() => reviewResults.value.review_analysis_results?.overall || reviewResults.value.overall_evaluation || {})

const primaryPaperFile = computed(() => {
  const documentFileId = paperResults.value.document?.file_id
  return resourceFiles.value.find((file: any) => file.file_id === documentFileId) || resourceFiles.value.find((file: any) => file.resource_type === 'paper') || null
})

const originalPaperFile = computed(() => {
  const paperFileId = reviewResults.value.document?.paper_file_id
  return resourceFiles.value.find((file: any) => file.file_id === paperFileId) || resourceFiles.value.find((file: any) => file.resource_type === 'review_paper') || null
})

const reviewFile = computed(() => {
  const reviewFileId = reviewResults.value.document?.review_file_id
  return resourceFiles.value.find((file: any) => file.file_id === reviewFileId) || resourceFiles.value.find((file: any) => file.resource_type === 'review_file') || null
})

const fetchSummary = async () => {
  const response = await tasksApi.getTaskSummary()
  summary.value = {
    ...summary.value,
    ...response.data,
  }
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await tasksApi.getAllTasks({
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      task_type: taskTypeFilter.value === 'all' ? undefined : taskTypeFilter.value as 'image' | 'paper' | 'review',
    })
    tasks.value = response.data.tasks || []
    totalPages.value = response.data.total_pages || 1
    totalTasks.value = response.data.total_tasks || 0
    currentPage.value = response.data.current_page || currentPage.value
  } catch (error) {
    console.error('Failed to fetch resource tasks:', error)
    snackbar.showMessage('获取资源列表失败', 'error')
  } finally {
    loading.value = false
  }
}

const openDetail = async (task: any) => {
  selectedTaskSummary.value = task
  selectedTaskDetail.value = null
  detailDialog.value = true
  detailLoading.value = true

  try {
    const response = await tasksApi.getTaskDetail(task.task_id)
    selectedTaskDetail.value = response.data
  } catch (error) {
    console.error('Failed to fetch task detail:', error)
    snackbar.showMessage('获取资源详情失败', 'error')
    detailDialog.value = false
  } finally {
    detailLoading.value = false
  }
}

const closeDetail = () => {
  detailDialog.value = false
  selectedTaskSummary.value = null
  selectedTaskDetail.value = null
}

const openDeleteDialog = (task: any) => {
  selectedTaskSummary.value = task
  deleteDialog.value = true
}

const handleDelete = async () => {
  if (!selectedTaskSummary.value) return

  deleteLoading.value = true
  try {
    await tasksApi.deleteTask(selectedTaskSummary.value.task_id)
    snackbar.showMessage('资源删除成功', 'success')
    deleteDialog.value = false
    if (detailDialog.value) closeDetail()
    await fetchSummary()
    await fetchTasks()
  } catch (error) {
    console.error('Failed to delete task:', error)
    snackbar.showMessage('删除资源失败', 'error')
  } finally {
    deleteLoading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchTasks()
}

const handlePageSizeChange = (size: number | string) => {
  pageSize.value = Number(size)
  currentPage.value = 1
  fetchTasks()
}

const taskTypeLabel = (taskType: string) => ({
  image: '图像',
  paper: '论文',
  review: '评审',
}[taskType] || '资源')

const taskTypeColor = (taskType: string) => ({
  image: 'primary',
  paper: 'deep-orange',
  review: 'teal',
}[taskType] || 'grey')

const statusLabel = (status: string) => ({
  pending: '待处理',
  in_progress: '进行中',
  completed: '已完成',
  failed: '失败',
}[status] || '未知')

const statusColor = (status: string) => ({
  pending: 'warning',
  in_progress: 'info',
  completed: 'success',
  failed: 'error',
}[status] || 'grey')

const formatDate = (value: string | null | undefined) => value || '-'

const formatConfidence = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(2)
}

const resolveAssetUrl = (url: string | null | undefined) => {
  if (!url) return null
  if (/^https?:\/\//.test(url)) return url
  const base = import.meta.env.VITE_API_URL || ''
  if (!base) return url
  return `${base.replace(/\/$/, '')}/${url.replace(/^\//, '')}`
}

const openResolvedLink = (url: string | null | undefined) => {
  if (!url) return
  window.open(url, '_blank', 'noopener')
}

const openLink = (url: string | null | undefined) => {
  openResolvedLink(resolveAssetUrl(url))
}

const openResourceFile = (file: any) => {
  if (!file?.file_available || !file?.download_url) {
    snackbar.showMessage(file?.download_message || '当前服务器无法访问该资源文件', 'warning')
    return
  }
  openLink(file.download_url)
}

const getImagePreviewUrl = (result: any) => resolveAssetUrl(result?.image_url)

watch([keyword, taskTypeFilter], () => {
  currentPage.value = 1
  fetchTasks()
})

onMounted(async () => {
  try {
    await fetchSummary()
    await fetchTasks()
  } catch (error) {
    console.error('Failed to initialize resource management:', error)
  }
})
</script>

<style scoped>
.page-shell {
  max-width: 1440px;
}

.stat-card,
.overview-card,
.summary-card {
  padding: 20px;
}

.detail-shell {
  max-width: 1440px;
  margin: 0 auto;
}

@media (max-width: 600px) {
  .page-shell {
    padding-left: 0;
    padding-right: 0;
  }

  .detail-shell {
    padding: 0;
  }
}
</style>
