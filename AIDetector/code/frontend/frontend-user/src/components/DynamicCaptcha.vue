<template>
  <div class="captcha-wrapper" @click="handleClick">
    <canvas ref="captchaCanvas" :width="width" :height="height"></canvas>
    <v-icon class="refresh-icon" icon="mdi-refresh" size="small"></v-icon>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, defineEmits } from 'vue'

const props = defineProps({
  width: {
    type: Number,
    default: 120
  },
  height: {
    type: Number,
    default: 40
  }
})

const emit = defineEmits(['update:code'])
const captchaCanvas = ref<HTMLCanvasElement | null>(null)
let captchaCode = ''
let isDrawing = false

// 生成随机验证码
const generateCode = (length: number = 4) => {
  const chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
  let code = ''
  for (let i = 0; i < length; i++) {
    code += chars[Math.floor(Math.random() * chars.length)]
  }
  return code
}

// 绘制验证码
const drawCaptcha = () => {
  if (isDrawing) return
  isDrawing = true

  const canvas = captchaCanvas.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  try {
    // 清空画布
    ctx.clearRect(0, 0, props.width, props.height)

    // 生成新的验证码
    captchaCode = generateCode()
    emit('update:code', captchaCode)

    // 设置背景
    ctx.fillStyle = '#f5f5f5'
    ctx.fillRect(0, 0, props.width, props.height)

    // 添加波浪线背景
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.05)'
    ctx.lineWidth = 1
  // 生成新的验证码
  captchaCode = generateCode()
  emit('update:code', captchaCode)

  // 设置背景
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, 0, props.width, props.height)

  // 添加波浪线背景
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.05)'
  ctx.lineWidth = 1
  for (let i = 0; i < 6; i++) {
    ctx.beginPath()
    let startX = 0
    let startY = Math.random() * props.height
    ctx.moveTo(startX, startY)
    for (let x = 0; x < props.width; x += 20) {
      const y = startY + Math.sin(x * 0.03) * 10
      ctx.lineTo(x, y)
    }
    ctx.stroke()
  }

  // 绘制文字
  const fontSize = props.height * 0.6
  ctx.font = `bold ${fontSize}px Arial`
  ctx.textBaseline = 'middle'

  // 随机颜色和位置绘制每个字符
  for (let i = 0; i < captchaCode.length; i++) {
    // 随机深色
    const r = Math.floor(Math.random() * 60)
    const g = Math.floor(Math.random() * 60)
    const b = Math.floor(Math.random() * 60)
    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`

    // 添加字符阴影
    ctx.shadowColor = 'rgba(0, 0, 0, 0.3)'
    ctx.shadowBlur = 2
    ctx.shadowOffsetX = 1
    ctx.shadowOffsetY = 1

    ctx.translate(props.width / 8 + i * props.width / 4, props.height / 2)
    ctx.rotate((Math.random() - 0.5) * 0.4)
    
    // 随机字体
    const fonts = ['Arial', 'Georgia', 'Verdana', 'Times New Roman']
    ctx.font = `bold ${fontSize}px ${fonts[Math.floor(Math.random() * fonts.length)]}`
    
    ctx.fillText(captchaCode[i], 0, Math.sin(i) * 3)
    ctx.setTransform(1, 0, 0, 1, 0, 0)
  }

  // 重置阴影
  ctx.shadowColor = 'transparent'
  ctx.shadowBlur = 0
  ctx.shadowOffsetX = 0
  ctx.shadowOffsetY = 0

  // 添加干扰线
  for (let i = 0; i < 4; i++) {
    const gradient = ctx.createLinearGradient(0, 0, props.width, props.height)
    gradient.addColorStop(0, `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.2)`)
    gradient.addColorStop(1, `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.2)`)
    ctx.strokeStyle = gradient
    ctx.lineWidth = Math.random() * 2 + 1
    
    ctx.beginPath()
    const startX = Math.random() * props.width
    const startY = Math.random() * props.height
    const cp1x = Math.random() * props.width
    const cp1y = Math.random() * props.height
    const cp2x = Math.random() * props.width
    const cp2y = Math.random() * props.height
    const endX = Math.random() * props.width
    const endY = Math.random() * props.height
    
    ctx.moveTo(startX, startY)
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, endX, endY)
    ctx.stroke()
  }

  // 添加干扰点和小圆圈
  for (let i = 0; i < 30; i++) {
    // 随机颜色
    const r = Math.floor(Math.random() * 255)
    const g = Math.floor(Math.random() * 255)
    const b = Math.floor(Math.random() * 255)
    
    // 绘制实心点
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.3)`
    ctx.beginPath()
    const x = Math.random() * props.width
    const y = Math.random() * props.height
    const radius = Math.random() * 2 + 1
    ctx.arc(x, y, radius, 0, 2 * Math.PI)
    ctx.fill()
    
    // 绘制空心圆
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.2)`
    ctx.lineWidth = 0.5
    ctx.beginPath()
    const x2 = Math.random() * props.width
    const y2 = Math.random() * props.height
    const radius2 = Math.random() * 4 + 2
    ctx.arc(x2, y2, radius2, 0, 2 * Math.PI)
    ctx.stroke()
  }
  } finally {
    isDrawing = false
  }
}

// 处理点击事件
const handleClick = (event: MouseEvent) => {
  // 防止事件冒泡
  event.stopPropagation()
  drawCaptcha()
}

onMounted(() => {
  drawCaptcha()
})

defineExpose({
  refreshCaptcha: drawCaptcha,
  getCode: () => captchaCode
})
</script>

<style scoped>
.captcha-wrapper {
  position: relative;
  display: inline-block;
  cursor: pointer;
  user-select: none;
}

.refresh-icon {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.captcha-wrapper:hover .refresh-icon {
  opacity: 0.6;
}

canvas {
  border-radius: 4px;
  vertical-align: middle;
}
</style> 