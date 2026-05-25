<template>
  <v-container class="workspace-shell llm-page" fluid>
    <v-card class="page-hero mb-6">
      <v-card-text class="pa-8 pa-md-10">
        <div class="d-flex flex-column flex-lg-row align-start align-lg-center justify-space-between ga-6">
          <div>
            <div class="section-eyebrow mb-3">Model Center</div>
            <h1 class="hero-title mb-4">模型配置与管理</h1>
            <p class="hero-copy">
              管理对话模型与 FastDetect 检测服务。启用后的配置会用于后续新任务，密钥不会在页面中明文展示。
            </p>
          </div>
          <v-btn color="primary" size="large" rounded="lg" prepend-icon="mdi-plus" @click="openDialog()">
            新增配置
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-row class="mb-4">
      <v-col cols="12" sm="6" lg="3">
        <div class="metric-card">
          <div class="d-flex align-center justify-space-between mb-4">
            <span class="subtle-text">全部配置</span>
            <v-icon color="primary">mdi-view-dashboard-outline</v-icon>
          </div>
          <div class="metric-value">{{ stats.total }}</div>
          <div class="text-body-2 subtle-text">当前记录数</div>
        </div>
      </v-col>
      <v-col cols="12" sm="6" lg="3">
        <div class="metric-card">
          <div class="d-flex align-center justify-space-between mb-4">
            <span class="subtle-text">已启用</span>
            <v-icon color="success">mdi-toggle-switch-outline</v-icon>
          </div>
          <div class="metric-value">{{ stats.active }}</div>
          <div class="text-body-2 subtle-text">可用于后续任务</div>
        </div>
      </v-col>
      <v-col cols="12" sm="6" lg="3">
        <div class="metric-card">
          <div class="d-flex align-center justify-space-between mb-4">
            <span class="subtle-text">FastDetect</span>
            <v-icon :color="stats.fastdetectReady ? 'success' : 'warning'">mdi-radar</v-icon>
          </div>
          <div class="metric-value">{{ stats.fastdetectReady ? '已就绪' : '待配置' }}</div>
          <div class="text-body-2 subtle-text">论文与 Review 段落检测</div>
        </div>
      </v-col>
      <v-col cols="12" sm="6" lg="3">
        <div class="metric-card">
          <div class="d-flex align-center justify-space-between mb-4">
            <span class="subtle-text">对话模型</span>
            <v-icon :color="stats.chatReady ? 'success' : 'warning'">mdi-message-processing-outline</v-icon>
          </div>
          <div class="metric-value">{{ stats.chatReady ? '可用' : '待配置' }}</div>
          <div class="text-body-2 subtle-text">解释、总结与辅助审查</div>
        </div>
      </v-col>
    </v-row>

    <v-row class="mb-6">
      <v-col cols="12">
        <v-card class="soft-card h-100">
          <v-card-text class="pa-6">
            <div class="d-flex flex-column flex-md-row align-md-center justify-space-between ga-4 mb-5">
              <div>
                <div class="text-h6 font-weight-bold">配置列表</div>
                <div class="text-body-2 subtle-text mt-1">建议只保留一个启用的 FastDetect 配置，避免误用旧密钥。</div>
              </div>
              <v-text-field
                v-model="search"
                max-width="320"
                density="comfortable"
                variant="outlined"
                rounded="lg"
                hide-details
                clearable
                prepend-inner-icon="mdi-magnify"
                label="搜索配置"
              />
            </div>

            <v-data-table
              :headers="headers"
              :items="filteredModels"
              :loading="loading"
              hover
              class="model-table"
            >
              <template #item.display_name="{ item }">
                <div class="py-2">
                  <div class="font-weight-bold">{{ item.display_name }}</div>
                  <div class="text-caption subtle-text">{{ item.model_name }}</div>
                </div>
              </template>

              <template #item.model_type="{ item }">
                <v-chip size="small" :color="item.model_type === 'fastdetect' ? 'deep-orange' : 'primary'" variant="tonal" class="aid-chip">
                  {{ modelTypeText(item.model_type) }}
                </v-chip>
              </template>

              <template #item.endpoint="{ item }">
                <span class="endpoint-text">{{ item.endpoint || '未填写' }}</span>
              </template>

              <template #item.has_api_key="{ item }">
                <v-chip size="small" :color="item.has_api_key ? 'success' : 'warning'" variant="tonal" class="aid-chip">
                  {{ item.has_api_key ? '密钥已保存' : '待填写密钥' }}
                </v-chip>
              </template>

              <template #item.is_active="{ item }">
                <v-switch
                  v-model="item.is_active"
                  color="success"
                  hide-details
                  density="compact"
                  inset
                  @change="toggleActive(item)"
                />
              </template>

              <template #item.actions="{ item }">
                <div class="d-flex justify-end ga-2">
                  <v-btn icon="mdi-pencil" size="small" variant="tonal" color="primary" @click="openDialog(item)" />
                  <v-btn icon="mdi-delete-outline" size="small" variant="text" color="error" @click="confirmDelete(item)" />
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="dialog" max-width="880px" persistent>
      <v-card class="config-dialog">
        <v-card-title class="pa-6 pb-2">
          <div>
            <div class="text-h5 font-weight-bold">{{ editingId ? '编辑模型配置' : '新增模型配置' }}</div>
            <div class="text-body-2 subtle-text mt-1">
              {{ editingId ? '只填写需要变更的内容；密钥留空会保持原值。' : '创建后即可在列表中启用或停用。' }}
            </div>
          </div>
        </v-card-title>

        <v-card-text class="pa-6">
          <v-row>
            <v-col cols="12" md="5">
              <div class="form-section h-100">
                <div class="section-title">用途</div>
                <v-btn-toggle
                  v-model="formData.model_type"
                  color="primary"
                  mandatory
                  class="type-toggle"
                  rounded="lg"
                >
                  <v-btn value="chat" class="px-5">
                    <v-icon start>mdi-message-processing-outline</v-icon>
                    对话模型
                  </v-btn>
                  <v-btn value="fastdetect" class="px-5">
                    <v-icon start>mdi-radar</v-icon>
                    FastDetect
                  </v-btn>
                </v-btn-toggle>
                <div class="text-body-2 subtle-text mt-4">
                  {{ formData.model_type === 'fastdetect'
                    ? '用于论文和 Review 的 AIGC 段落概率检测。'
                    : '用于生成解释、总结和辅助审查内容。' }}
                </div>
              </div>
            </v-col>

            <v-col cols="12" md="7">
              <div class="form-section">
                <div class="section-title">基础信息</div>
                <v-row>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="formData.display_name" label="显示名称" variant="outlined" rounded="lg" required />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="formData.model_name" label="模型/检测器名称" variant="outlined" rounded="lg" required />
                  </v-col>
                  <v-col cols="12" sm="6">
                    <v-text-field v-model="formData.provider" label="服务来源" variant="outlined" rounded="lg" required />
                  </v-col>
                  <v-col cols="12" sm="6" class="d-flex align-center">
                    <v-switch v-model="formData.is_active" label="启用配置" color="success" hide-details inset />
                  </v-col>
                </v-row>
              </div>
            </v-col>

            <v-col cols="12">
              <div class="form-section">
                <div class="section-title">连接信息</div>
                <v-row>
                  <v-col cols="12">
                    <v-text-field
                      v-model="formData.endpoint"
                      label="服务地址"
                      variant="outlined"
                      rounded="lg"
                      placeholder="例如：https://api.fastdetect.net/api/detect"
                    />
                  </v-col>
                  <v-col cols="12">
                    <v-text-field
                      v-model="formData.api_key"
                      :label="editingId ? '密钥（留空保持不变）' : '密钥'"
                      :type="showApiKey ? 'text' : 'password'"
                      :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                      variant="outlined"
                      rounded="lg"
                      autocomplete="off"
                      @click:append-inner="showApiKey = !showApiKey"
                    />
                  </v-col>
                  <v-col cols="12">
                    <v-textarea
                      v-model="formData.description"
                      label="备注"
                      rows="3"
                      auto-grow
                      variant="outlined"
                      rounded="lg"
                    />
                  </v-col>
                </v-row>
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="px-6 pb-6">
          <v-spacer />
          <v-btn variant="text" rounded="lg" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" rounded="lg" :loading="saving" @click="save">保存配置</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="430px">
      <v-card>
        <v-card-title class="text-h6 font-weight-bold pa-6 pb-2">删除配置</v-card-title>
        <v-card-text class="px-6">
          确定删除“{{ itemToDelete?.display_name }}”吗？删除后不会再用于新任务。
        </v-card-text>
        <v-card-actions class="px-6 pb-6">
          <v-spacer />
          <v-btn variant="text" rounded="lg" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" rounded="lg" :loading="deleting" @click="executeDelete">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getLLMModels, createLLMModel, updateLLMModel, deleteLLMModel } from '@/api/llm'
import type { LLMModel } from '@/api/llm'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()

const dialog = ref(false)
const deleteDialog = ref(false)
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const showApiKey = ref(false)
const search = ref('')
const models = ref<LLMModel[]>([])
const itemToDelete = ref<LLMModel | null>(null)
const editingId = ref<number | null>(null)

const formData = ref<Partial<LLMModel>>(defaultForm())

const headers = [
  { title: '配置名称', align: 'start', key: 'display_name' },
  { title: '用途', key: 'model_type' },
  { title: '服务来源', key: 'provider' },
  { title: '服务地址', key: 'endpoint' },
  { title: '密钥状态', key: 'has_api_key' },
  { title: '启用', key: 'is_active' },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
] as const

const filteredModels = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return models.value
  return models.value.filter((item) => {
    return [
      item.display_name,
      item.model_name,
      item.provider,
      item.model_type,
      item.endpoint,
    ].some((value) => String(value || '').toLowerCase().includes(keyword))
  })
})

const stats = computed(() => {
  const active = models.value.filter((item) => item.is_active)
  return {
    total: models.value.length,
    active: active.length,
    fastdetectReady: active.some((item) => item.model_type === 'fastdetect' && item.has_api_key),
    chatReady: active.some((item) => item.model_type === 'chat' && item.has_api_key),
  }
})

watch(
  () => formData.value.model_type,
  (nextType) => {
    if (nextType === 'fastdetect') {
      if (!formData.value.provider || formData.value.provider === 'openai_compat') {
        formData.value.provider = 'fastdetect'
      }
      if (!formData.value.endpoint) {
        formData.value.endpoint = 'https://api.fastdetect.net/api/detect'
      }
      if (!formData.value.model_name) {
        formData.value.model_name = 'fast-detect(llama3-8b/llama3-8b-instruct)'
      }
      if (!formData.value.display_name) {
        formData.value.display_name = 'FastDetect AIGC 检测'
      }
    } else if (!formData.value.provider || formData.value.provider === 'fastdetect') {
      formData.value.provider = 'openai_compat'
    }
  },
)

function defaultForm(): Partial<LLMModel> {
  return {
    model_name: '',
    display_name: '',
    provider: 'openai_compat',
    model_type: 'chat',
    endpoint: '',
    api_key: '',
    is_active: true,
    description: '',
  }
}


function modelTypeText(value?: string) {
  if (value === 'fastdetect') return 'FastDetect'
  return '对话模型'
}

async function fetchModels() {
  loading.value = true
  try {
    const res = await getLLMModels()
    models.value = res.data || res
  } catch (err) {
    console.error(err)
    snackbar.showMessage('模型配置加载失败', 'error')
  } finally {
    loading.value = false
  }
}

function openDialog(item?: LLMModel) {
  if (item) {
    editingId.value = item.id
    formData.value = { ...item, api_key: '' }
  } else {
    editingId.value = null
    formData.value = defaultForm()
  }
  showApiKey.value = false
  dialog.value = true
}

async function save() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateLLMModel(editingId.value, formData.value)
    } else {
      await createLLMModel(formData.value)
    }
    dialog.value = false
    snackbar.showMessage('配置已保存', 'success')
    await fetchModels()
  } catch (err) {
    console.error(err)
    snackbar.showMessage('保存失败，请检查填写内容', 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(item: LLMModel) {
  itemToDelete.value = item
  deleteDialog.value = true
}

async function executeDelete() {
  if (!itemToDelete.value) return
  deleting.value = true
  try {
    await deleteLLMModel(itemToDelete.value.id)
    deleteDialog.value = false
    snackbar.showMessage('配置已删除', 'success')
    await fetchModels()
  } catch (err) {
    console.error(err)
    snackbar.showMessage('删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

async function toggleActive(item: LLMModel) {
  try {
    await updateLLMModel(item.id, { is_active: item.is_active })
    snackbar.showMessage(item.is_active ? '配置已启用' : '配置已停用', 'success')
  } catch (err) {
    item.is_active = !item.is_active
    console.error(err)
    snackbar.showMessage('状态更新失败', 'error')
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.model-table :deep(.v-data-table__td) {
  vertical-align: middle;
}

.endpoint-text {
  display: inline-block;
  max-width: 260px;
  overflow: hidden;
  color: #667085;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.config-dialog {
  overflow: hidden;
}

.form-section {
  padding: 18px;
  border: 1px solid rgba(23, 32, 51, 0.08);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.72);
}

.section-title {
  margin-bottom: 16px;
  font-weight: 900;
  color: #172033;
}

.type-toggle {
  flex-wrap: wrap;
}

@media (max-width: 720px) {
  .endpoint-text {
    max-width: 180px;
  }
}
</style>
