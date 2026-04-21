<template>
  <v-card class="chart-card" elevation="2">
    <v-card-title class="text-h5 font-weight-bold primary--text py-4">
      <v-icon large color="primary" class="mr-2">mdi-chart-bar</v-icon>
      各学科检测方法使用频率
    </v-card-title>
    <v-card-text>
      <div ref="chartRef" class="chart-wrapper"></div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import analyticsApi from '@/api/analytics'
import { useSnackbarStore } from '@/stores/snackbar'

const chartRef = ref<HTMLElement | null>(null)
const chartInstance = ref<echarts.ECharts | null>(null)
const snackbar = useSnackbarStore()

// 响应式处理图表大小
const resizeHandler = () => {
  chartInstance.value?.resize()
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  // 清理之前的实例
  chartInstance.value?.dispose()
  chartInstance.value = echarts.init(chartRef.value)
  loadChartData()
}

// 加载数据并渲染图表
const loadChartData = async () => {
  try {
    const res = await analyticsApi.getDetectionMethodStats()
    if (res.data) {
      renderChart(res.data)
    }
  } catch (e) {
    console.error('获取数据失败:', e)
    snackbar.showMessage('获取检测方法统计数据失败')
  }
}

// 渲染图表
const renderChart = (data: Record<string, Record<string, number>>) => {
  const methodList = Array.from({ length: 7 }, (_, i) => `Method-${i + 1}`)
  const colorPalette = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452']

  // 构建堆叠图的系列
  const series = methodList.map((method, index) => ({
    name: method,
    type: 'bar',
    stack: 'total',
    emphasis: { focus: 'series' },
    itemStyle: { color: colorPalette[index] },
    data: Object.keys(data).map(tag => {
      const value = data[tag][method] || 0
      const total = data[tag].total || 1
      return {
        value,
        percent: ((value / total) * 100).toFixed(1) + '%'
      }
    })
  }))

  // 配置图表
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter(params: any) {
        const category = params[0].axisValue
        let html = `<strong>${category}</strong><br/>`
        params.forEach((item: any) => {
          html += `${item.seriesName}: <strong>${item.data.value}</strong> (${item.data.percent})<br/>`
        })
        return html
      },
      backgroundColor: '#ffffff',
      borderColor: '#ccc',
      borderWidth: 1,
      textStyle: { color: '#333' },
      padding: [10, 15],
      extraCssText: 'box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 8px;'
    },
    legend: {
      data: methodList,
      bottom: 0,
      textStyle: { fontSize: 12, color: '#333' },
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 16
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '18%',
      top: '6%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: Object.keys(data),
      axisLabel: { rotate: 30, fontSize: 12, color: '#333' },
      axisLine: { lineStyle: { color: '#ccc' } }
    },
    yAxis: {
      type: 'value',
      name: '使用次数',
      axisLabel: { color: '#333' },
      nameTextStyle: { color: '#333' },
      axisLine: { lineStyle: { color: '#ccc' } },
      splitLine: { lineStyle: { color: '#eee' } }
    },
  }

  // 设置图表配置
  chartInstance.value?.setOption(option)
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  chartInstance.value?.dispose()
  chartInstance.value = null
  window.removeEventListener('resize', resizeHandler)
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
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
}

.chart-wrapper {
  width: 100%;
  height: 400px;
}

@media (max-width: 600px) {
  .chart-wrapper {
    height: 300px;
  }
}
</style>
