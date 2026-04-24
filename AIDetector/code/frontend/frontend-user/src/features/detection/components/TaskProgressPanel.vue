<template>
  <div class="upload-progress">
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" class="mr-2 return-btn" @click="emit('back')">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回上传</span>
    </div>

    <v-card>
      <v-card-text v-if="taskType === 'image'">
        <ImageSelectionStep v-if="fileId" :file-id="fileId" @update="emit('update-selected-images', $event)" @tag-changed="emit('update-tag', $event)" @add-name="emit('update-name', $event)" />
      </v-card-text>
      <v-card-actions v-if="taskType === 'image'">
        <v-spacer />
        <v-btn color="primary" variant="elevated" append-icon="mdi-arrow-right" :disabled="!canProceed" :loading="submittingDetection" @click="emit('submit-image-task')">
          提交检测
        </v-btn>
      </v-card-actions>

      <template v-else>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            上传完成，请确认任务信息后创建检测任务。
          </v-alert>

          <v-list lines="two" class="mb-4">
            <v-list-item v-for="item in uploadedResourceFiles" :key="item.file_id">
              <template #prepend>
                <v-icon color="primary">mdi-file-document-outline</v-icon>
              </template>
              <v-list-item-title>{{ item.name }}</v-list-item-title>
              <v-list-item-subtitle>资源类型：{{ item.resource_type }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <v-select :model-value="resourceDomainTag" :items="resourceDomainOptions" item-title="title" item-value="value" label="学科领域" placeholder="请选择学科领域" variant="outlined" density="comfortable" class="mb-4" @update:model-value="emit('update:resourceDomainTag', $event)" />

          <v-text-field :model-value="resourceTaskName" label="任务名称" placeholder="请输入任务名称" variant="outlined" density="comfortable" maxlength="64" counter @update:model-value="emit('update:resourceTaskName', $event)" />

          <template v-if="taskType === 'paper'">
            <v-divider class="my-4" />
            <v-switch
              :model-value="paperEnableImageDetection"
              :disabled="!paperImageDetectionSupported"
              color="primary"
              inset
              label="提取论文中的图像并执行图像检测"
              hide-details
              class="mb-3"
              @update:model-value="handlePaperToggle"
            />
            <div class="text-caption text-medium-emphasis mb-3">
              {{ paperImageDetectionHint }}
            </div>
            <div v-if="paperEnableImageDetection && paperImageDetectionSupported" class="d-flex flex-wrap align-center ga-3">
              <v-btn variant="outlined" color="primary" @click="emit('configure-paper-methods')">
                选择论文图像检测子任务
              </v-btn>
              <v-chip color="primary" variant="tonal">
                已选 {{ selectedPaperMethodCount }}/9 项
              </v-chip>
            </div>

            <v-divider class="my-4" />
            <div class="d-flex justify-space-between align-center mb-3">
              <div>
                <div class="text-subtitle-1 font-weight-medium">提取文本预览（可编辑）</div>
                <div class="text-caption text-medium-emphasis">点击按钮在弹窗中查看并修改文本。</div>
              </div>
              <v-btn color="primary" variant="outlined" @click="paperPreviewDialog = true">
                打开文本预览窗口
              </v-btn>
            </div>

            <v-dialog v-model="paperPreviewDialog" max-width="960">
              <v-card class="paper-preview-card">
                <v-card-title>
                  <span>论文文本预览与编辑</span>
                </v-card-title>
                <v-card-text class="paper-preview-content">
                  <v-alert
                    v-if="paperTextPreviewError"
                    type="warning"
                    variant="tonal"
                    class="mb-3"
                  >
                    {{ paperTextPreviewError }}
                  </v-alert>
                  <v-textarea
                    :model-value="paperEditableText"
                    :loading="paperTextPreviewLoading"
                    label="论文文本（可在创建任务前修改）"
                    placeholder="未获取到提取文本，可点击右上角重新提取。"
                    variant="outlined"
                    rows="16"
                    auto-grow
                    @update:model-value="emit('update:paperEditableText', String($event || ''))"
                  />
                  <div class="text-caption text-medium-emphasis mt-2">
                    说明：你在这里修改的文本将作为本次论文检测的输入。
                  </div>
                </v-card-text>
                <v-card-actions class="paper-preview-actions">
                  <v-btn
                    variant="outlined"
                    color="primary"
                    :loading="paperTextPreviewLoading"
                    @click="emit('reload-paper-text-preview')"
                  >
                    重新提取文字
                  </v-btn>
                  <v-spacer />
                  <v-btn color="primary" @click="paperPreviewDialog = false">保存并关闭</v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </template>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="elevated" append-icon="mdi-arrow-right" @click="emit('submit-resource-task')">
            创建任务
          </v-btn>
        </v-card-actions>
      </template>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import ImageSelectionStep from '@/components/steps/ImageSelectionStep.vue'
import type { DetectionType, TaskOption, UploadedResourceFile } from '../types'
import { ref } from 'vue'

defineProps<{
  taskType: DetectionType
  fileId: number | null
  uploadedResourceFiles: UploadedResourceFile[]
  resourceDomainTag: string
  resourceDomainOptions: TaskOption[]
  resourceTaskName: string
  canProceed: boolean
  submittingDetection: boolean
  paperEnableImageDetection: boolean
  paperImageDetectionSupported: boolean
  paperImageDetectionHint: string
  selectedPaperMethodCount: number
  paperEditableText: string
  paperTextPreviewLoading: boolean
  paperTextPreviewError: string
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'submit-image-task'): void
  (e: 'submit-resource-task'): void
  (e: 'configure-paper-methods'): void
  (e: 'reload-paper-text-preview'): void
  (e: 'update-selected-images', images: any[]): void
  (e: 'update-tag', tag: string): void
  (e: 'update-name', name: string): void
  (e: 'update:resourceDomainTag', value: string): void
  (e: 'update:resourceTaskName', value: string): void
  (e: 'update:paperEnableImageDetection', value: boolean): void
  (e: 'update:paperEditableText', value: string): void
}>()

const handlePaperToggle = (value: boolean | null) => {
  emit('update:paperEnableImageDetection', Boolean(value))
}

const paperPreviewDialog = ref(false)
</script>

<style scoped>
.upload-progress {
  position: relative;
  min-height: 100vh;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.paper-preview-card {
  max-height: 82vh;
  display: flex;
  flex-direction: column;
}

.paper-preview-content {
  overflow-y: auto;
}

.paper-preview-actions {
  position: sticky;
  bottom: 0;
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  z-index: 2;
}
</style>
