<template>
  <v-dialog :model-value="modelValue" max-width="760" @update:model-value="emit('update:modelValue', $event)">
    <v-card rounded="lg">
      <v-card-title class="d-flex align-center justify-space-between">
        <span class="text-h6">选择检测任务</span>
        <v-btn icon="mdi-close" variant="text" @click="closeDialog" />
      </v-card-title>

      <v-card-subtitle class="pb-2">
        选择这次图片检测要执行的方法。默认全选，未勾选的方法不会进入本次检测。
      </v-card-subtitle>

      <v-card-text>
        <div class="d-flex justify-space-between align-center mb-4">
          <div class="text-body-2 text-medium-emphasis">
            已选择 {{ selectedCount }}/{{ METHOD_OPTIONS.length }} 项
          </div>
          <v-btn variant="text" color="primary" @click="toggleSelectAll">
            {{ allSelected ? '全不选' : '全选' }}
          </v-btn>
        </div>

        <v-row>
          <v-col
            v-for="option in METHOD_OPTIONS"
            :key="option.key"
            cols="12"
            md="6"
          >
            <v-checkbox
              v-model="selectedMap[option.key]"
              color="primary"
              hide-details
            >
              <template #label>
                <div>
                  <div class="text-body-1">{{ option.label }}</div>
                  <div class="text-caption text-medium-emphasis">{{ option.description }}</div>
                </div>
              </template>
            </v-checkbox>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="px-6 pb-6">
        <v-spacer />
        <v-btn variant="text" @click="closeDialog">取消</v-btn>
        <v-btn color="primary" @click="confirmSelection">
          确认并提交
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

const METHOD_OPTIONS = [
  { key: 'llm', label: '大语言模型多模态识别', description: '结合视觉与文本推理判断是否存在学术造假痕迹。' },
  { key: 'ela', label: '误差级分析（ELA）', description: '通过 JPEG 重压缩误差寻找局部编辑异常。' },
  { key: 'exif', label: 'EXIF 元数据检查', description: '检查软件痕迹和时间字段异常。' },
  { key: 'cmd', label: '复制移动伪造检测', description: '检测同一图像内部的拷贝粘贴区域。' },
  { key: 'urn_coarse_v2', label: '拼接检测', description: '使用高精度卷积网络检测图像拼接。' },
  { key: 'urn_blurring', label: '模糊处理检测', description: '检测局部模糊或擦除后的异常区域。' },
  { key: 'urn_brute_force', label: '极端处理检测', description: '检测超分辨率、强去噪等重处理痕迹。' },
  { key: 'urn_contrast', label: '对比度异常检测', description: '发现局部对比度与整体统计分布不一致的区域。' },
  { key: 'urn_inpainting', label: 'AI 填充区域检测', description: '识别修补、生成式填充和局部重绘痕迹。' },
] as const

type MethodKey = (typeof METHOD_OPTIONS)[number]['key']
type MethodSwitches = Record<MethodKey, boolean>

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', value: MethodSwitches): void
}>()

const createDefaultSelection = (): MethodSwitches => ({
  llm: true,
  ela: true,
  exif: true,
  cmd: true,
  urn_coarse_v2: true,
  urn_blurring: true,
  urn_brute_force: true,
  urn_contrast: true,
  urn_inpainting: true,
})

const selectedMap = reactive<MethodSwitches>(createDefaultSelection())

const resetSelection = () => {
  Object.assign(selectedMap, createDefaultSelection())
}

watch(
  () => props.modelValue,
  (opened) => {
    if (opened) {
      resetSelection()
    }
  },
)

const selectedCount = computed(() => Object.values(selectedMap).filter(Boolean).length)
const allSelected = computed(() => selectedCount.value === METHOD_OPTIONS.length)

const closeDialog = () => {
  emit('update:modelValue', false)
}

const toggleSelectAll = () => {
  const nextValue = !allSelected.value
  for (const option of METHOD_OPTIONS) {
    selectedMap[option.key] = nextValue
  }
}

const confirmSelection = () => {
  emit('confirm', { ...selectedMap })
  closeDialog()
}
</script>
