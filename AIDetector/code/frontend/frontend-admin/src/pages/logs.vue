<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">Event Logs</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">Unified event view for uploads, detections, and review operations.</div>
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end align-end">
        <v-btn color="success" prepend-icon="mdi-download" @click="downloadLogs">
          Download CSV
        </v-btn>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-select v-model="operationType" :items="operationTypeOptions" label="Operation Type" variant="outlined" hide-details clearable />
      </v-col>
      <v-col cols="12" md="6">
        <v-text-field v-model="organization" prepend-inner-icon="mdi-office-building" label="Organization Filter" variant="outlined" hide-details clearable />
      </v-col>
    </v-row>

    <EventLogTable :title="'Admin Event Stream'" :headers="headers" :items="logs" :loading="loading" :total="totalLogs" />

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
import { onMounted, ref, watch } from 'vue'
import logsApi from '@/api/logs'
import EventLogTable from '@/features/logs/EventLogTable.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const headers = [
  { title: 'User', key: 'user', align: 'start' as const },
  { title: 'Organization', key: 'organization', align: 'start' as const },
  { title: 'Operation', key: 'operation_type', align: 'center' as const },
  { title: 'Model', key: 'related_model', align: 'center' as const },
  { title: 'Related ID', key: 'related_id', align: 'center' as const },
  { title: 'Time', key: 'operation_time', align: 'center' as const },
]

const operationTypeOptions = [
  { title: 'Upload', value: 'upload' },
  { title: 'Detection', value: 'detection' },
  { title: 'Review Request', value: 'review_request' },
  { title: 'Manual Review', value: 'manual_review' },
]

const loading = ref(false)
const logs = ref<any[]>([])
const totalLogs = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(10)
const operationType = ref<string | null>(null)
const organization = ref('')

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await logsApi.getEventLogs({
      page: currentPage.value,
      page_size: pageSize.value,
      operation_type: operationType.value || '',
      organization: organization.value || '',
    })
    const { logs: items, total_logs, current_page, total_pages } = response.data
    logs.value = items || []
    totalLogs.value = total_logs || 0
    currentPage.value = current_page || 1
    totalPages.value = total_pages || 1
  } catch (error) {
    console.error('Failed to fetch event logs:', error)
    snackbar.showMessage('Failed to fetch event logs.', 'error')
  } finally {
    loading.value = false
  }
}

const downloadLogs = async () => {
  try {
    const response = await logsApi.downloadEventLogs({
      operation_type: operationType.value || '',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'event_logs.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    snackbar.showMessage('Event logs downloaded.', 'success')
  } catch (error) {
    console.error('Failed to download event logs:', error)
    snackbar.showMessage('Failed to download event logs.', 'error')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchLogs()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchLogs()
}

watch([operationType, organization], () => {
  currentPage.value = 1
  fetchLogs()
})

onMounted(fetchLogs)
</script>

<style scoped>
.page-shell {
  max-width: 1400px;
}
</style>
