import re

with open('/Users/kxq/Desktop/BUAA-SE-AID/AIDetector/code/frontend/frontend-user/src/features/detection/components/TaskProgressPanel.vue', 'r') as f:
    content = f.read()

# Add select to template
select_html = """
          <template v-if="taskType === 'paper' || taskType === 'review'">
            <v-select
              :model-value="selectedLlmModel"
              :items="activeModels"
              item-title="display_name"
              item-value="model_name"
              label="使用的AI大模型 (用于文本检测和推断分析)"
              placeholder="默认使用系统预设大语言模型"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              clearable
              @update:model-value="emit('update:selectedLlmModel', $event)"
            />
          </template>

          <template v-if="taskType === 'paper'">"""

content = content.replace("          <template v-if=\"taskType === 'paper'\">", select_html)


# Add to imports
import_str = "import type { DetectionType, TaskOption, UploadedResourceFile } from '../types'\nimport type { LLMModel } from '@/api/llm'"
content = content.replace("import type { DetectionType, TaskOption, UploadedResourceFile } from '../types'", import_str)


# Add to props
props_replace = """  const props = defineProps<{
    taskType: DetectionType
    fileId: number | null
    uploadedResourceFiles: UploadedResourceFile[]
    resourceDomainTag: string
    resourceDomainOptions: TaskOption[]
    resourceTaskName: string
    activeModels: LLMModel[]
    selectedLlmModel: string | undefined
    canProceed: boolean"""

content = re.sub(r"  const props = defineProps<{\n    taskType: DetectionType\n    fileId: number \| null\n    uploadedResourceFiles: UploadedResourceFile\[\]\n    resourceDomainTag: string\n    resourceDomainOptions: TaskOption\[\]\n    resourceTaskName: string\n    canProceed: boolean", props_replace, content)

# Add to emits
emits_replace = """  const emit = defineEmits<{
    (e: 'back'): void
    (e: 'submit-image-task'): void
    (e: 'submit-resource-task'): void
    (e: 'configure-paper-methods'): void
    (e: 'reload-paper-text-preview'): void
    (e: 'reload-review-paper-text-preview'): void
    (e: 'reload-review-text-preview'): void
    (e: 'update-selected-images', images: any[]): void
    (e: 'update-tag', tag: string): void
    (e: 'update-name', name: string): void
    (e: 'update:resourceDomainTag', value: string): void
    (e: 'update:resourceTaskName', value: string): void
    (e: 'update:selectedLlmModel', value: string | undefined): void
    (e: 'update:paperEnableImageDetection', value: boolean): void"""

content = re.sub(r"  const emit = defineEmits<{\n    \(e: 'back'\): void\n    \(e: 'submit-image-task'\): void\n    \(e: 'submit-resource-task'\): void\n    \(e: 'configure-paper-methods'\): void\n    \(e: 'reload-paper-text-preview'\): void\n    \(e: 'reload-review-paper-text-preview'\): void\n    \(e: 'reload-review-text-preview'\): void\n    \(e: 'update-selected-images', images: any\[\]\): void\n    \(e: 'update-tag', tag: string\): void\n    \(e: 'update-name', name: string\): void\n    \(e: 'update:resourceDomainTag', value: string\): void\n    \(e: 'update:resourceTaskName', value: string\): void\n    \(e: 'update:paperEnableImageDetection', value: boolean\): void", emits_replace, content)

with open('/Users/kxq/Desktop/BUAA-SE-AID/AIDetector/code/frontend/frontend-user/src/features/detection/components/TaskProgressPanel.vue', 'w') as f:
    f.write(content)

