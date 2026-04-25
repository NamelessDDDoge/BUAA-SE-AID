<template>
  <v-card elevation="2" rounded="lg">
    <v-card-title class="d-flex align-center">
      <span class="text-h6">{{ title }}</span>
      <v-spacer />
      <span class="text-caption text-medium-emphasis">共 {{ total }} 条记录</span>
    </v-card-title>
    <v-data-table :headers="headers" :items="items" :loading="loading" hide-default-footer>
      <template #item.operation_type="{ item }">
        <v-chip size="small" :color="operationTypeColor(item.operation_type)">{{ operationTypeLabel(item.operation_type) }}</v-chip>
      </template>
      <template #item.related_model="{ item }">
        <v-chip size="small" :color="modelColor(item.related_model)" variant="tonal">{{ modelLabel(item.related_model) }}</v-chip>
      </template>
      <template #no-data>
        <div class="py-8 text-center text-medium-emphasis">暂无日志数据</div>
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
  total: number
}>()

const operationTypeLabel = (type: string) => ({
  upload: '上传',
  detection: '检测',
  review_request: '评审申请',
  manual_review: '人工审核',
}[type] || type)

const operationTypeColor = (type: string) => ({
  upload: 'info',
  detection: 'success',
  review_request: 'warning',
  manual_review: 'primary',
}[type] || 'grey')

const modelColor = (model: string) => ({
  DetectionTask: 'info',
  FileManagement: 'primary',
  ReviewRequest: 'warning',
  ManualReview: 'success',
}[model] || 'grey')

const modelLabel = (model: string) => ({
  DetectionTask: '检测任务',
  FileManagement: '文件资源',
  ReviewRequest: '评审申请',
  ManualReview: '人工审核',
}[model] || model)
</script>
