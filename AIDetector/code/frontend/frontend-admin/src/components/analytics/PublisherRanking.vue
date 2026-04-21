<template>
  <v-card class="mb-6 chart-card scrollable-card" elevation="2">
    <v-card-title class="text-h5 font-weight-bold primary--text py-4">
      <v-icon large color="primary" class="mr-2">mdi-account-group</v-icon>
      编辑排行榜
    </v-card-title>
    <v-card-text class="pa-4">
      <v-table class="publisher-table">
        <thead>
          <tr>
            <th class="text-left">排名</th>
            <th class="text-left">用户名</th>
            <th class="text-right">总任务数</th>
            <th class="text-right">总图片数</th>
            <th class="text-right">造假数量</th>
            <th class="text-right">造假比例</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(publisher, index) in publishers" :key="publisher.username">
            <td>{{ index + 1 }}</td>
            <td>{{ publisher.username }}</td>
            <td class="text-right">{{ publisher.total_tasks }}</td>
            <td class="text-right">{{ publisher.total_images }}</td>
            <td class="text-right">{{ publisher.fake_count }}</td>
            <td class="text-right">
              <v-chip :color="getFakeRatioColor(publisher.fake_ratio)" text-color="white" size="small">
                {{ (publisher.fake_ratio * 100).toFixed(1) }}%
              </v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import analyticsApi from '@/api/analytics'

const publishers = ref<any[]>([])

const getFakeRatioColor = (ratio: number): string => {
  if (ratio >= 0.5) return 'error'
  if (ratio >= 0.3) return 'warning'
  if (ratio >= 0.1) return 'info'
  return 'success'
}

const fetchPublishersData = async () => {
  try {
    const res = await analyticsApi.getTopPublishers()
    if (res.data && Array.isArray(res.data)) {
      publishers.value = res.data.map(p => ({
        ...p,
        fake_ratio: p.fake_count / (p.total_images || 1)
      }))
    }
  } catch (error) {
    console.error('获取排行榜数据失败:', error)
  }
}

onMounted(() => {
  fetchPublishersData()
})
</script>

<style scoped>
.chart-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.scrollable-card {
  overflow-y: auto;
  max-height: 600px;
}

.scrollable-card::-webkit-scrollbar {
  width: 6px;
}

.scrollable-card::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.scrollable-card::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 3px;
}

.scrollable-card::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.sticky-header {
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 1;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.publisher-table {
  width: 100%;
}

@media (max-width: 600px) {
  .scrollable-card {
    max-height: 400px;
  }
}
</style> 