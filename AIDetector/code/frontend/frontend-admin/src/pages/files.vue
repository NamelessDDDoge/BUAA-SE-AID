<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">Task Overview</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">
          Task-centric admin view for image, paper, and review lanes.
        </div>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="keyword"
          prepend-inner-icon="mdi-magnify"
          label="Search Tasks"
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
          <div class="text-overline">All Tasks</div>
          <div class="text-h4 font-weight-bold">{{ summary.total_task_count }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" elevation="2" class="stat-card">
          <div class="text-overline">Completed</div>
          <div class="text-h4 font-weight-bold">{{ summary.completed_task_count }}</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="lg" elevation="2" class="stat-card">
          <div class="text-overline">Recent 30 Days</div>
          <div class="text-h4 font-weight-bold">{{ summary.recent_task_count }}</div>
        </v-card>
      </v-col>
    </v-row>

    <TaskSummaryTable :title="tableTitle" :headers="headers" :items="tasks" :loading="loading" />

    <div class="d-flex align-center justify-center pa-4">
      <div class="d-flex align-center">
        <span class="text-caption mr-2">Rows per page</span>
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
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import tasksApi from '@/api/tasks'
import TaskTypeFilter from '@/features/tasks/TaskTypeFilter.vue'
import TaskSummaryTable from '@/features/tasks/TaskSummaryTable.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const loading = ref(false)
const keyword = ref('')
const taskTypeFilter = ref('all')
const pageSize = ref(10)
const currentPage = ref(1)
const totalPages = ref(1)
const tasks = ref<any[]>([])
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

const headers = [
  { title: 'Task ID', key: 'task_id', align: 'center' as const },
  { title: 'Task Name', key: 'task_name', align: 'start' as const },
  { title: 'Type', key: 'task_type', align: 'center' as const },
  { title: 'Status', key: 'status', align: 'center' as const },
  { title: 'Publisher', key: 'username', align: 'start' as const },
  { title: 'Organization', key: 'organization', align: 'start' as const },
  { title: 'Uploaded', key: 'upload_time', align: 'center' as const },
]

const taskTypeOptions = computed(() => [
  { label: 'All', value: 'all', color: 'grey', count: summary.value.total_task_count },
  { label: 'Image', value: 'image', color: 'primary', count: summary.value.task_type_counts.image },
  { label: 'Paper', value: 'paper', color: 'deep-orange', count: summary.value.task_type_counts.paper },
  { label: 'Review', value: 'review', color: 'teal', count: summary.value.task_type_counts.review },
])

const tableTitle = computed(() => {
  if (taskTypeFilter.value === 'all') return 'Recent Tasks'
  return `${taskTypeFilter.value[0].toUpperCase()}${taskTypeFilter.value.slice(1)} Tasks`
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
  } catch (error) {
    console.error('Failed to fetch admin tasks:', error)
    snackbar.showMessage('Failed to load admin task data.', 'error')
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchTasks()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTasks()
}

watch([keyword, taskTypeFilter], () => {
  currentPage.value = 1
  fetchTasks()
})

onMounted(async () => {
  try {
    await fetchSummary()
    await fetchTasks()
  } catch (error) {
    console.error('Failed to initialize task overview:', error)
  }
})
</script>

<style scoped>
.page-shell {
  max-width: 1400px;
}

.stat-card {
  padding: 20px;
}
</style>
