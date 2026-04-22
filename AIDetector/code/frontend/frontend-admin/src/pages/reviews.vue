<template>
  <v-container class="page-shell">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">Review Operations</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">
          Review requests stay visible here, but the page now opens with a review-lane task perspective.
        </div>
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="searchQuery"
          label="Search Publisher"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          variant="outlined"
          hide-details
          @keyup.enter="fetchRequests"
        />
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12">
        <TaskTypeFilter v-model="taskTypeFilter" :options="taskTypeOptions" />
      </v-col>
    </v-row>

    <TaskSummaryTable :title="'Review Lane Tasks'" :headers="taskHeaders" :items="reviewTasks" :loading="loadingTasks" class="mb-6" />

    <v-card elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center">
        <span class="text-h6">Review Requests</span>
        <v-spacer />
        <span class="text-caption text-medium-emphasis">{{ totalRequests }} rows</span>
      </v-card-title>
      <v-data-table :headers="headers" :items="requests" :loading="loadingRequests" hide-default-footer>
        <template #item.state="{ item }">
          <v-chip size="small" :color="getStateColor(item.state)">{{ getStateName(item.state) }}</v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-eye" variant="text" color="primary" @click="openReviewDialog(item)" />
        </template>
      </v-data-table>
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
    </v-card>

    <v-dialog v-model="showReviewDialog" max-width="800">
      <v-card class="elevation-4">
        <v-card-title class="text-h6 font-weight-bold">Review Request Detail</v-card-title>
        <v-card-text>
          <div v-if="selectedRequest" class="d-flex flex-column ga-4">
            <div class="d-flex align-center">
              <v-avatar size="40" class="mr-4">
                <v-img :src="selectedRequest.avatar || 'https://randomuser.me/api/portraits/lego/1.jpg'" :alt="selectedRequest.username" />
              </v-avatar>
              <div>
                <div class="text-h6">{{ selectedRequest.username }}</div>
                <div class="text-caption text-medium-emphasis">{{ selectedRequest.time }}</div>
              </div>
            </div>

            <v-chip :color="getStateColor(selectedRequest.state)" size="small">{{ getStateName(selectedRequest.state) }}</v-chip>

            <div v-if="reviewDetails" class="d-flex flex-column ga-4">
              <div v-if="reviewDetails.reason">
                <div class="text-subtitle-1 font-weight-bold mb-2">Reason</div>
                <div class="text-body-1">{{ reviewDetails.reason }}</div>
              </div>

              <div>
                <div class="text-subtitle-1 font-weight-bold mb-2">Assigned Reviewers</div>
                <div class="d-flex flex-wrap ga-4">
                  <div v-for="person in reviewDetails.persons" :key="person.id" class="d-flex align-center">
                    <v-avatar size="32" class="mr-2">
                      <v-img :src="getImageUrl(person.avatar)" :alt="person.username" />
                    </v-avatar>
                    <span>{{ person.username }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="error" variant="text" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(0)">Reject</v-btn>
          <v-btn color="success" :disabled="!selectedRequest || selectedRequest.state !== 'pending'" @click="handleReviewRequest(1)">Approve</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import reviewApi from '@/api/review'
import tasksApi from '@/api/tasks'
import TaskTypeFilter from '@/features/tasks/TaskTypeFilter.vue'
import TaskSummaryTable from '@/features/tasks/TaskSummaryTable.vue'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

interface ReviewRequest {
  id: number
  username: string
  avatar: string
  state: string
  time: string
}

const headers = [
  { title: 'Publisher', key: 'username', align: 'start' as const },
  { title: 'State', key: 'state', align: 'center' as const },
  { title: 'Submitted', key: 'time', align: 'center' as const },
  { title: 'Actions', key: 'actions', align: 'center' as const, sortable: false },
]

const taskHeaders = [
  { title: 'Task ID', key: 'task_id', align: 'center' as const },
  { title: 'Task Name', key: 'task_name', align: 'start' as const },
  { title: 'Type', key: 'task_type', align: 'center' as const },
  { title: 'Status', key: 'status', align: 'center' as const },
  { title: 'Publisher', key: 'username', align: 'start' as const },
  { title: 'Uploaded', key: 'upload_time', align: 'center' as const },
]

const taskTypeFilter = ref('review')
const taskTypeOptions = [
  { label: 'Review', value: 'review', color: 'teal' },
  { label: 'Paper', value: 'paper', color: 'deep-orange' },
]

const requests = ref<ReviewRequest[]>([])
const reviewTasks = ref<any[]>([])
const loadingRequests = ref(false)
const loadingTasks = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalRequests = ref(0)
const totalPages = ref(1)
const searchQuery = ref('')
const showReviewDialog = ref(false)
const selectedRequest = ref<ReviewRequest | null>(null)
const reviewDetails = ref<any>(null)
const rejectReason = ref('')

const getImageUrl = (url: string) => import.meta.env.VITE_API_URL + url

const getStateColor = (state: string) => ({
  pending: 'warning',
  refused: 'error',
  accepted: 'success',
}[state] || 'grey')

const getStateName = (state: string) => ({
  pending: 'Pending',
  refused: 'Rejected',
  accepted: 'Approved',
}[state] || state)

const fetchReviewTasks = async () => {
  loadingTasks.value = true
  try {
    const response = await tasksApi.getAllTasks({
      page: 1,
      page_size: 6,
      task_type: taskTypeFilter.value as 'paper' | 'review',
    })
    reviewTasks.value = response.data.tasks || []
  } catch (error) {
    console.error('Failed to load review-lane tasks:', error)
  } finally {
    loadingTasks.value = false
  }
}

const fetchRequests = async () => {
  loadingRequests.value = true
  try {
    const response = await reviewApi.getReviewRequests({
      page: currentPage.value,
      page_size: pageSize.value,
      query: searchQuery.value || '',
    })
    const { requests: requestList, current_page, total_pages, total_requests } = response.data
    requests.value = requestList.map((request: any) => ({
      id: request.id,
      username: request.username,
      avatar: request.avatar ? import.meta.env.VITE_API_URL + request.avatar : '',
      state: request.state,
      time: request.time,
    }))
    currentPage.value = current_page
    totalPages.value = total_pages
    totalRequests.value = total_requests
  } catch (error) {
    console.error('Failed to fetch review requests:', error)
    snackbar.showMessage('Failed to fetch review requests.', 'error')
  } finally {
    loadingRequests.value = false
  }
}

const openReviewDialog = async (request: ReviewRequest) => {
  selectedRequest.value = request
  try {
    const response = await reviewApi.getReviewRequestDetails(request.id)
    reviewDetails.value = response.data
    showReviewDialog.value = true
  } catch (error) {
    console.error('Failed to fetch review request detail:', error)
    snackbar.showMessage('Failed to fetch review request detail.', 'error')
  }
}

const handleReviewRequest = async (choice: number) => {
  if (!selectedRequest.value) return
  try {
    await reviewApi.handleReviewRequest(selectedRequest.value.id, {
      choice,
      reason: rejectReason.value,
    })
    snackbar.showMessage(choice === 1 ? 'Review request approved.' : 'Review request rejected.', 'success')
    showReviewDialog.value = false
    rejectReason.value = ''
    await fetchRequests()
  } catch (error) {
    console.error('Failed to handle review request:', error)
    snackbar.showMessage('Failed to handle the review request.', 'error')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchRequests()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchRequests()
}

watch(taskTypeFilter, fetchReviewTasks)

onMounted(async () => {
  await fetchReviewTasks()
  await fetchRequests()
})
</script>

<style scoped>
.page-shell {
  max-width: 1400px;
}
</style>
