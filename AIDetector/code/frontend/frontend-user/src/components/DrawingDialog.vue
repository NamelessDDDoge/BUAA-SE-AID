<template>
  <v-dialog v-model="dialog" max-width="90vw" persistent>
    <v-card class="drawing-dialog">
      <v-card-title class="d-flex justify-space-between align-center pa-4">
        <span>绘制标注</span>
        <v-btn icon="mdi-close" variant="text" @click="handleClose"></v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <div class="drawing-container">
          <!-- 左侧工具栏 -->
          <div class="toolbar pa-4">
            <div class="color-picker mb-4">
              <div class="text-subtitle-2 mb-2">选择颜色</div>
              <div class="color-grid">
                <div v-for="color in colors" :key="color.value" class="color-item"
                  :class="{ active: selectedColor === color.value }" :style="{ backgroundColor: color.value }"
                  @click="handleColorSelect(color.value)"></div>
              </div>
            </div>

            <v-divider class="mb-4"></v-divider>

            <div class="tools">
              <v-btn block color="error" variant="tonal" class="mb-2" @click="clearDrawing">
                <v-icon start>mdi-eraser</v-icon>
                清除绘制
              </v-btn>
              <v-btn block color="primary" variant="tonal" @click="handleSave">
                <v-icon start>mdi-content-save</v-icon>
                保存
              </v-btn>
            </div>
          </div>

          <!-- 右侧绘制区域 -->
          <div class="drawing-area">
            <div class="image-container">
              <img :src="imageUrl" ref="imageRef" @load="handleImageLoad" class="preview-image" />
              <canvas ref="canvasRef" class="drawing-canvas" :class="{ 'is-drawing': isDrawing }"
                @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp"
                @mouseleave="handleMouseUp"></canvas>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

interface Props {
  modelValue: boolean
  imageUrl: string
  initialPaths?: Array<{
    points: Array<{ x: number; y: number }>
    color: string
  }>
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue', 'save'])

const dialog = ref(props.modelValue)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const ctx = ref<CanvasRenderingContext2D | null>(null)
const isDrawing = ref(false)
const currentPath = ref<Array<{ x: number; y: number }>>([])
const paths = ref<Array<{ points: Array<{ x: number; y: number }>; color: string }>>(
  props.initialPaths || []
)

const colors = [
  { name: '红色', value: '#FF0000' },
  { name: '蓝色', value: '#0000FF' },
  { name: '绿色', value: '#00FF00' },
  { name: '黄色', value: '#FFFF00' },
  { name: '紫色', value: '#800080' },
]

const selectedColor = ref(colors[0].value)

// 监听弹窗状态
watch(() => props.modelValue, (val) => {
  dialog.value = val
  if (val) {
    nextTick(() => {
      initCanvas()
    })
  }
})

watch(dialog, (val) => {
  emit('update:modelValue', val)
})

// 选择颜色
const handleColorSelect = (color: string) => {
  selectedColor.value = color
  isDrawing.value = true
  // 更新当前绘制路径的颜色
  if (ctx.value) {
    ctx.value.strokeStyle = color
  }
}

// 初始化Canvas
const initCanvas = () => {
  if (!canvasRef.value || !imageRef.value) return

  const canvas = canvasRef.value
  const image = imageRef.value
  const container = image.parentElement

  if (!container) return

  // 设置canvas尺寸与图片实际显示尺寸一致
  canvas.width = image.offsetWidth
  canvas.height = image.offsetHeight

  // 设置canvas样式尺寸和位置
  canvas.style.width = `${image.offsetWidth}px`
  canvas.style.height = `${image.offsetHeight}px`
  canvas.style.position = 'absolute'
  canvas.style.top = '0'
  canvas.style.left = '0'

  ctx.value = canvas.getContext('2d', { alpha: true })
  if (ctx.value) {
    ctx.value.lineWidth = 2
    ctx.value.lineCap = 'round'
    ctx.value.lineJoin = 'round'
    ctx.value.strokeStyle = selectedColor.value
  }

  redrawAllPaths()
}

// 获取鼠标在canvas上的相对坐标
const getMousePosition = (e: MouseEvent) => {
  if (!canvasRef.value) return null

  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()

  // 计算缩放比例
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height

  // 计算实际坐标
  const x = (e.clientX - rect.left) * scaleX
  const y = (e.clientY - rect.top) * scaleY

  return { x, y }
}

// 处理图片加载
const handleImageLoad = () => {
  initCanvas()
}

// 绘制事件处理
const handleMouseDown = (e: MouseEvent) => {
  // 只响应鼠标左键
  if (e.button !== 0) return

  if (!ctx.value || !canvasRef.value) return

  const pos = getMousePosition(e)
  if (!pos) return

  // 开始新的绘制路径
  currentPath.value = [{ x: pos.x, y: pos.y }]

  ctx.value.beginPath()
  ctx.value.moveTo(pos.x, pos.y)
  ctx.value.strokeStyle = selectedColor.value
}

const handleMouseMove = (e: MouseEvent) => {
  // 只在按住鼠标左键时绘制
  if (!ctx.value || !canvasRef.value || e.buttons !== 1) return

  const pos = getMousePosition(e)
  if (!pos) return

  // 如果还没有开始绘制，则开始新的路径
  if (currentPath.value.length === 0) {
    currentPath.value = [{ x: pos.x, y: pos.y }]
    ctx.value.beginPath()
    ctx.value.moveTo(pos.x, pos.y)
    ctx.value.strokeStyle = selectedColor.value
  }

  currentPath.value.push({ x: pos.x, y: pos.y })
  ctx.value.lineTo(pos.x, pos.y)
  ctx.value.stroke()
}

const handleMouseUp = (e: MouseEvent) => {
  // 只响应鼠标左键
  if (e.button !== 0) return

  if (!ctx.value) return

  if (currentPath.value.length > 0) {
    paths.value.push({
      points: [...currentPath.value],
      color: selectedColor.value,
    })
    currentPath.value = []
  }
}

// 重绘所有路径
const redrawAllPaths = () => {
  if (!ctx.value || !canvasRef.value) return

  ctx.value.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  paths.value = props.initialPaths || []

  paths.value.forEach((path) => {
    if (path.points.length > 0) {
      ctx.value!.strokeStyle = path.color
      ctx.value?.beginPath()
      ctx.value?.moveTo(path.points[0].x, path.points[0].y)
      path.points.forEach((point) => {
        ctx.value?.lineTo(point.x, point.y)
      })
      ctx.value?.stroke()
    }
  })
}

// 清除绘制
const clearDrawing = () => {
  paths.value = []
  if (ctx.value && canvasRef.value) {
    ctx.value.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  }
}

// 保存绘制结果
const handleSave = () => {
  emit('save', paths.value)
  handleClose()
}

// 关闭弹窗
const handleClose = () => {
  dialog.value = false
}

// 监听窗口大小变化
onMounted(() => {
  window.addEventListener('resize', initCanvas)
})

onUnmounted(() => {
  window.removeEventListener('resize', initCanvas)
})

// 监听图片加载完成
watch(() => props.imageUrl, () => {
  // 等待图片加载完成
  if (imageRef.value) {
    if (imageRef.value.complete) {
      nextTick(() => {
        initCanvas()
      })
    } else {
      imageRef.value.onload = () => {
        nextTick(() => {
          initCanvas()
        })
      }
    }
  }
}, { immediate: true })
</script>

<style scoped>
.drawing-dialog {
  height: 90vh;
}

.drawing-container {
  display: flex;
  height: calc(90vh - 64px);
}

.toolbar {
  width: 200px;
  border-right: 1px solid rgba(0, 0, 0, 0.12);
  background-color: rgb(var(--v-theme-surface));
}

.drawing-area {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f5f5;
  overflow: hidden;
}

.image-container {
  position: relative;
  display: inline-block;
  max-width: 100%;
  max-height: calc(90vh - 64px);
}

.preview-image {
  max-width: 100%;
  max-height: calc(90vh - 64px);
  object-fit: contain;
  display: block;
}

.drawing-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  touch-action: none;
}

.drawing-canvas.is-drawing {
  pointer-events: auto;
  cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'/%3E%3C/svg%3E") 0 24, auto !important;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.color-item {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.color-item:hover {
  transform: scale(1.1);
}

.color-item.active {
  border-color: rgba(0, 0, 0, 0.5);
}
</style>