<template>
  <v-container class="analytics-container">
    <v-row class="mb-6">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold">Analytics</h1>
        <div class="text-body-2 text-medium-emphasis mt-2">
          Analytics now start from task types, then fan out into the existing organization and activity views.
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" md="4">
        <TaskTypeCharts :counts="taskTypeCounts" />
      </v-col>
      <v-col cols="12" md="8">
        <TaskTrend />
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <ImageTagStats />
      </v-col>
      <v-col cols="12" md="6">
        <PublisherRanking v-if="isOrganizationAdmin" />
        <OrgRanking v-else />
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12">
        <ActiveUserTrend v-if="isOrganizationAdmin" />
        <ActiveOrgTrend v-else />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import ImageTagStats from '@/components/analytics/ImageTagStats.vue'
import PublisherRanking from '@/components/analytics/PublisherRanking.vue'
import OrgRanking from '@/components/analytics/OrgRanking.vue'
import TaskTrend from '@/components/analytics/TaskTrend.vue'
import ActiveUserTrend from '@/components/analytics/ActiveUserTrend.vue'
import ActiveOrgTrend from '@/components/analytics/ActiveOrgTrend.vue'
import TaskTypeCharts from '@/features/analytics/TaskTypeCharts.vue'
import tasksApi from '@/api/tasks'
import userApi from '@/api/user'

const isOrganizationAdmin = ref(false)
const taskTypeCounts = ref({
  image: 0,
  paper: 0,
  review: 0,
})

onMounted(async () => {
  try {
    const [userRes, taskSummaryRes] = await Promise.all([
      userApi.getUserInfo(),
      tasksApi.getTaskSummary(),
    ])
    isOrganizationAdmin.value = userRes.data.admin_type === 'organization_admin'
    taskTypeCounts.value = taskSummaryRes.data.task_type_counts || taskTypeCounts.value
  } catch (error) {
    console.error('Failed to load analytics context:', error)
  }
})
</script>

<style scoped>
.analytics-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

@media (max-width: 600px) {
  .analytics-container {
    padding: 12px;
  }
}
</style>
