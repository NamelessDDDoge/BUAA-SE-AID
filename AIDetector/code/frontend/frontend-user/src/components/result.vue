<template>
  <div class="task-detail pa-4">
    <!-- 主要内容区域 -->
    <div class="main-content rounded-lg">
      <!-- 顶部信息区域 -->
      <div class="info-section pa-6">
        <div class="content-wrapper d-flex justify-center">
          <div class="content-container">
            <div class="info-content d-flex align-center justify-center pa-4">
              <!-- 进度和标签 -->
              <div class="d-flex align-center">
                <div class="progress-circle mr-3 elevation-1">
                  <span class="text-h5 font-weight-bold primary--text">{{ formatNumber(props.ai_detection) }}</span>
                  <span class="text-caption">为假</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分割线 -->
      <v-divider></v-divider>

      <!-- 主要内容区域 -->
      <div class="content-wrapper d-flex pa-2 justify-center">
        <div class="content-container d-flex" style="gap: 12px;">
          <!-- 图片预览区域 -->
          <div class="preview-section">
            <div class="preview-box">
              <v-img v-if="props.imageUrl" :src="props.imageUrl" contain height="100%" class="rounded-lg">
                <template v-slot:placeholder>
                  <div class="d-flex align-center justify-center fill-height">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  </div>
                </template>
              </v-img>
              <span v-else class="text-h4">PIC</span>

              <!-- 添加标注层 -->
              <div class="annotation-layer" v-if="props.imageUrl">
                <svg class="annotation-svg">
                  <g v-for="(dimensionAnnotations, dimensionIndex) in props.annotations" :key="dimensionIndex">
                    <g v-if="showAnnotations[dimensionIndex]">
                      <g v-for="(annotationObject, objIndex) in dimensionAnnotations" :key="objIndex">
                        <!-- 添加连接线 -->
                        <polyline :points="annotationObject.points.map(p => `${p.x},${p.y}`).join(' ')"
                          :stroke="annotationObject.color" stroke-width="7" fill="none" opacity="0.7"
                          stroke-linecap="round" stroke-linejoin="round" />
                        <!-- 保持原有的点 -->
                        <circle v-for="(point, pointIndex) in annotationObject.points" :key="pointIndex" :cx="point.x"
                          :cy="point.y" r="4" :fill="annotationObject.color" :stroke="annotationObject.color"
                          stroke-width="2" opacity="0.7" />
                      </g>
                    </g>
                  </g>
                </svg>
              </div>
            </div>
          </div>

          <!-- 评分维度区域 -->
          <div class="dimension-section rounded-lg elevation-1">
            <div class="text-h6 font-weight-medium mb-4">人工审查结果</div>
            <div class="dimension-list">
              <div v-for="(dimension, index) in dimensions" :key="index" class="dimension-item mb-6">
                <div class="d-flex align-center justify-space-between mb-2">
                  <span class="text-subtitle-1">{{ dimension.name }}</span>
                  <v-btn v-if="props.annotations[index]?.length > 0" size="small" variant="text" color="primary"
                    class="annotation-btn" @click="toggleAnnotations(index)">
                    <v-icon start>{{ showAnnotations[index] ? 'mdi-eye-off' : 'mdi-eye' }}</v-icon>
                    {{ showAnnotations[index] ? '隐藏标注' : '显示标注' }}
                  </v-btn>
                </div>
                <div class="degree-result mb-2">
                  <div class="d-flex align-center">
                    <v-icon :color="getDegreeColor(props.scores[index])" class="mr-2">
                      {{ getDegreeIcon(props.scores[index]) }}
                    </v-icon>
                    <span class="text-body-1">{{ getDegreeLabel(props.scores[index]) }}</span>
                  </div>
                </div>
                <div class="reason-text mt-2">
                  <div class="text-caption text-grey">理由：</div>
                  <div class="text-body-2">{{ props.reasons[index] || '暂无理由' }}</div>
                </div>
              </div>

              <!-- 造假判定结果 -->
              <div class="fake-judge-section mt-4 pt-4">
                <div class="text-subtitle-1 mb-4">造假判定</div>
                <div class="d-flex align-center">
                  <v-icon :color="props.result === true ? 'success' : 'error'" class="mr-2">
                    {{ props.result === true ? 'mdi-check-circle' : 'mdi-alert-circle' }}
                  </v-icon>
                  <span class="text-body-1">
                    {{ props.result === true ? '真实图片' : '造假图片' }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps({
  taskId: {
    type: String,
    required: false,
    default: null,
  },
  imageUrl: {
    type: String,
    required: false,
    default: "",
  },
  reasons: {
    type: Array as PropType<string[]>,
    required: true,
    default: () => [],
  },
  result: {
    type: Boolean,
    required: true,
    default: () => false
  },
  scores: {
    type: Array as PropType<number[]>,
    required: true,
    default: () => []
  },
  ai_detection: {
    type: Number,
    required: true,
    default: () => 0
  },
  // 添加标注点集合属性，适应 Canvas 坐标格式
  annotations: {
    type: Array as PropType<Array<Array<{ points: { x: number, y: number }[], color: string }>>>,
    required: true,
    default: () => []
  }
});

const formatNumber = (result: number) => {
  return `${(result * 100).toFixed(2)}%`
}


// 评分维度数据
interface Dimension {
  name: string;
  value: number | null;
  reason: string;
  showFakeArea: boolean;
}

const dimensions = ref<Dimension[]>([
  {
    name: '高斯模糊',
    value: props.scores[0],
    reason: props.reasons[0],
    showFakeArea: false
  },
  {
    name: '亮度/对比度调节',
    value: props.scores[1],
    reason: props.reasons[1],
    showFakeArea: false
  },
  {
    name: '智能修复',
    value: props.scores[2],
    reason: props.reasons[2],
    showFakeArea: false
  },
  {
    name: '暴力覆盖',
    value: props.scores[3],
    reason: props.reasons[3],
    showFakeArea: false
  },
  {
    name: '同图复制',
    value: props.scores[4],
    reason: props.reasons[4],
    showFakeArea: false
  },
  {
    name: '重叠切割',
    value: props.scores[5],
    reason: props.reasons[5],
    showFakeArea: false
  },
  {
    name: '跨图拼接',
    value: props.scores[6],
    reason: props.reasons[6],
    showFakeArea: false
  }
])


const getDegreeColor = (value: number | null) => {
  if (value === null) return 'grey'
  switch (value) {
    case 1:
      return 'success'
    case 2:
      return 'info'
    case 3:
      return 'yellow'
    case 4:
      return 'warning'
    case 5:
      return 'success'
    default:
      return 'error'
  }
}


const getDegreeIcon = (value: number | null) => {
  if (value === null) return 'mdi-emoticon-neutral'
  switch (value) {
    case 1:
      return 'mdi-emoticon-happy'
    case 2:
      return 'mdi-emoticon-smile'
    case 3:
      return 'mdi-emoticon-neutral'
    case 4:
      return 'mdi-emoticon-sad'
    case 5:
      return 'mdi-emoticon-frown'
    default:
      return 'mdi-emoticon-neutral'
  }
}

const getDegreeLabel = (value: number | null) => {
  if (value === null) return '未评分'
  switch (value) {
    case 1:
      return '基本没有'
    case 2:
      return '轻微'
    case 3:
      return '不明显'
    case 4:
      return '较严重'
    case 5:
      return '严重'
    default:
      return '未评分'
  }
}

// 图片造假判定数据
const imageJudgements = props.result

// 在 script setup 中添加
const showAnnotations = ref<boolean[]>(Array(dimensions.value.length).fill(false));

const toggleAnnotations = (index: number) => {
  showAnnotations.value[index] = !showAnnotations.value[index];
}

</script>

<style scoped>
.task-detail {
  position: relative;
  min-height: 100vh;
  max-height: 100vh;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.main-content {
  height: calc(100vh - 80px);
  overflow: hidden;
  background-color: rgb(var(--v-theme-surface));
}

.info-section {
  background-color: rgb(var(--v-theme-surface));
  padding: 16px 0;
}

.info-content {
  width: 100%;
  background-color: rgb(var(--v-theme-surface));
  min-height: 160px;
  padding: 12px 16px !important;
  justify-content: center;
  gap: 24px;
}

.progress-circle {
  width: clamp(100px, 8vw, 130px);
  height: clamp(100px, 8vw, 130px);
  border-radius: 50%;
  border: 5px solid rgb(var(--v-theme-primary));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-surface));
}

.progress-circle .text-h5 {
  font-size: clamp(1.8rem, 2vw, 2.5rem) !important;
  line-height: 1.2;
}

.progress-circle .text-caption {
  font-size: 1rem !important;
  margin-top: 4px;
}

.task-list {
  width: clamp(360px, 30vw, 420px);
  padding: 0 12px;
}

.task-item {
  width: 100%;
  margin-bottom: 12px;
}

.task-item .v-progress-linear {
  width: clamp(260px, 25vw, 340px) !important;
  height: 10px !important;
}

.task-item .text-h6 {
  white-space: nowrap;
}

.content-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.content-container {
  width: 100%;
  max-width: min(1200px, 95vw);
  display: flex;
  justify-content: center;
}

.task-stats {
  min-width: 320px;
  justify-content: center;
}

.answer-card {
  padding: 16px;
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-width: 280px;
  margin-right: 200px
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.answer-btn {
  width: 36px !important;
  min-width: 0 !important;
  height: 36px !important;
  padding: 0 !important;
}

@media (max-width: 1280px) {
  .task-stats {
    min-width: clamp(280px, 25vw, 320px);
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.image-list {
  width: clamp(100px, 8vw, 120px);
  height: calc(100vh - 380px);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.image-grid {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  margin-top: -8px;
}

.image-grid-item {
  width: 80px;
  height: 80px;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.2s ease;
  border: 2px solid transparent;
  flex-shrink: 0;
}

.image-grid-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.image-grid-item.active {
  border-color: rgb(var(--v-theme-primary));
}

.preview-section {
  flex: 1;
  min-width: 0;
  max-width: min(800px, 60vw);
  margin: 0 12px;
}

.preview-box {
  position: relative;
  height: calc(100vh - 380px);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  overflow: hidden;
}

.preview-box .v-img {
  max-width: 800px;
  max-height: 100%;
  object-fit: contain;
}

.preview-controls {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
}

.control-btn {
  opacity: 0.7;
  transition: opacity 0.2s ease !important;
}

.control-btn:hover {
  opacity: 1;
  transform: none;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-primary), 0.4);
}

@media (max-width: 960px) {
  .content-container {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .preview-section {
    max-width: 100%;
    order: -1;
  }

  .image-list {
    height: auto;
    min-height: 300px;
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.dimension-section {
  width: 360px;
  padding: 20px;
  background-color: rgb(var(--v-theme-surface));
  height: calc(100vh - 380px);
  overflow-y: auto;
}

.dimension-list {
  padding-right: 12px;
}

.dimension-item {
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.1);
  padding-bottom: 16px;
}

.dimension-item:last-child {
  border-bottom: none;
}

@media (max-width: 1280px) {
  .dimension-section {
    width: 260px;
  }
}

.fake-judge-section {
  border-top: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.degree-result {
  width: 100%;
}

.degree-result .v-icon {
  margin-right: 8px;
}

.reason-text {
  width: 100%;
}

.reason-text .text-caption {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-primary), 0.5);
}

.reason-text .text-body-2 {
  font-size: 0.875rem;
  margin-top: 4px;
}

.fake-area-btn {
  font-size: 0.75rem;
  text-transform: none;
  letter-spacing: 0;
  min-width: 120px;
  /* 确保按钮有固定的最小宽度 */
}

.review-comment {
  margin-top: 8px;
  padding: 8px;
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-radius: 4px;
}

.review-comment .text-caption {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-primary), 0.5);
}

.review-comment .text-body-2 {
  font-size: 0.875rem;
  margin-top: 4px;
  color: rgba(var(--v-theme-primary), 0.8);
}

.annotation-btn {
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.875rem;
}

.preview-box {
  position: relative;
  height: calc(100vh - 380px);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  overflow: hidden;
}

.annotation-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.annotation-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.annotation-svg circle {
  transition: all 0.3s ease;
}

.annotation-svg circle:hover {
  r: 6;
  opacity: 0.8;
}
</style>