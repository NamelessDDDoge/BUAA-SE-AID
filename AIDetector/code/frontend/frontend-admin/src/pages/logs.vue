<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">日志记录</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">统一查看上传、检测与评审相关操作日志。</div>
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end align-end">
        <v-btn color="success" prepend-icon="mdi-download" @click="downloadLogs">
          导出 CSV
        </v-btn>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-select v-model="operationType" :items="operationTypeOptions" label="操作类型" variant="outlined" hide-details clearable />
      </v-col>
      <v-col cols="12" md="6">
        <v-select
          v-model="organization"
          :items="organizationOptions"
          label="组织筛选"
          prepend-inner-icon="mdi-office-building"
          variant="outlined"
          hide-details
          clearable
          item-title="title"
          item-value="value"
        />
      </v-col>
    </v-row>

    <EventLogTable :title="'日志记录'" :headers="headers" :items="logs" :loading="loading" :total="totalLogs" />

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
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import logsApi from '@/api/logs'
import organizationApi from '@/api/organization'
import EventLogTable from '@/features/logger/EventLogTable.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const headers = [
  { title: '用户', key: 'user', align: 'start' as const },
  { title: '组织', key: 'organization', align: 'start' as const },
  { title: '操作类型', key: 'operation_type', align: 'center' as const },
  { title: '关联模型', key: 'related_model', align: 'center' as const },
  { title: '关联 ID', key: 'related_id', align: 'center' as const },
  { title: '操作时间', key: 'operation_time', align: 'center' as const },
]

const operationTypeOptions = [
  { title: '上传', value: 'upload' },
  { title: '检测', value: 'detection' },
  { title: '评审申请', value: 'review_request' },
  { title: '人工审核', value: 'manual_review' },
]

const loading = ref(false)
const logs = ref<any[]>([])
const totalLogs = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const pageSize = ref(10)
const operationType = ref<string | null>(null)
const organization = ref<number | null>(null)
const organizationOptions = ref<Array<{ title: string; value: number }>>([])

const fetchOrganizations = async () => {
  try {
    const response = await organizationApi.getOrgList({ page: 1, page_size: 1000 })
    const organizations = response.data.organizations || []
    organizationOptions.value = organizations.map((item: any) => ({
      title: item.name,
      value: item.id,
    }))
  } catch (error) {
    console.error('Failed to fetch organizations for log filter:', error)
    snackbar.showMessage('获取组织列表失败', 'error')
  }
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await logsApi.getEventLogs({
      page: currentPage.value,
      page_size: pageSize.value,
      operation_type: operationType.value || '',
      organization: organization.value ?? '',
    })
    const { logs: items, total_logs, current_page, total_pages } = response.data
    logs.value = items || []
    totalLogs.value = total_logs || 0
    currentPage.value = current_page || 1
    totalPages.value = total_pages || 1
  } catch (error) {
    console.error('Failed to fetch event logs:', error)
    snackbar.showMessage('获取日志失败', 'error')
  } finally {
    loading.value = false
  }
}

const downloadLogs = async () => {
  try {
    const response = await logsApi.downloadEventLogs({
      operation_type: operationType.value || '',
      organization: organization.value ?? undefined,
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'event_logs.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    snackbar.showMessage('日志导出成功', 'success')
  } catch (error) {
    console.error('Failed to download event logs:', error)
    snackbar.showMessage('日志导出失败', 'error')
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

onMounted(async () => {
  await fetchOrganizations()
  await fetchLogs()
})
</script>

<style scoped>
.page-shell {
  max-width: 1400px;
}
</style>
