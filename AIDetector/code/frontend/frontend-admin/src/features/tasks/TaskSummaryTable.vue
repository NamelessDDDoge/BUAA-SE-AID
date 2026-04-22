<template>
  <v-card elevation="2" rounded="lg">
    <v-card-title class="d-flex align-center">
      <span class="text-h6">{{ title }}</span>
      <v-spacer />
      <span class="text-caption text-medium-emphasis">{{ items.length }} rows</span>
    </v-card-title>
    <v-data-table :headers="headers" :items="items" :loading="loading" hide-default-footer>
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
      <template #no-data>
        <div class="py-8 text-center text-medium-emphasis">No tasks to display.</div>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  headers: any[]
  items: any[]
  loading?: boolean
}>()

const taskTypeLabel = (taskType: string) => ({
  image: 'Image',
  paper: 'Paper',
  review: 'Review',
}[taskType] || 'Unknown')

const taskTypeColor = (taskType: string) => ({
  image: 'primary',
  paper: 'deep-orange',
  review: 'teal',
}[taskType] || 'grey')

const statusLabel = (status: string) => ({
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
}[status] || 'Unknown')

const statusColor = (status: string) => ({
  pending: 'warning',
  in_progress: 'info',
  completed: 'success',
  failed: 'error',
}[status] || 'grey')
</script>
