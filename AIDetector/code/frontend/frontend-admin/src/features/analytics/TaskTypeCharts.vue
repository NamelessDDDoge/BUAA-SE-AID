<template>
  <v-card class="chart-card" elevation="3">
    <v-card-title class="text-h6 font-weight-medium">
      <v-icon color="primary" class="mr-2">mdi-chart-donut</v-icon>
      Task Type Distribution
    </v-card-title>
    <v-card-text>
      <div ref="chartRef" class="chart-container"></div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  counts: {
    image: number
    paper: number
    review: number
  }
}>()

const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const renderChart = () => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        data: [
          { value: props.counts.image, name: 'Image' },
          { value: props.counts.paper, name: 'Paper' },
          { value: props.counts.review, name: 'Review' },
        ],
      },
    ],
  })
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  chartInstance = null
  window.removeEventListener('resize', handleResize)
})

watch(() => props.counts, renderChart, { deep: true })
</script>

<style scoped>
.chart-card {
  border-radius: 12px;
}

.chart-container {
  width: 100%;
  height: 320px;
}
</style>
