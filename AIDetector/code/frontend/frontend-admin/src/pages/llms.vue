<template>
  <v-container>
    <v-row class="mb-6 align-center">
      <v-col>
        <h1 class="text-h4 font-weight-bold">大模型管理</h1>
      </v-col>
      <v-col cols="auto">
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog()">
          新增模型
        </v-btn>
      </v-col>
    </v-row>

    <v-card>
      <v-data-table
        :headers="headers"
        :items="models"
        :loading="loading"
        hover
      >
        <template v-slot:item.is_active="{ item }">
          <v-switch
            v-model="item.is_active"
            color="success"
            hide-details
            density="compact"
            @change="toggleActive(item)"
          ></v-switch>
        </template>
        <template v-slot:item.model_type="{ item }">
          <v-chip size="small" :color="item.model_type === 'fastdetect' ? 'deep-orange' : 'primary'" variant="tonal">
            {{ modelTypeText(item.model_type) }}
          </v-chip>
        </template>
        <template v-slot:item.has_api_key="{ item }">
          <v-chip size="small" :color="item.has_api_key ? 'success' : 'warning'" variant="tonal">
            {{ item.has_api_key ? '已配置' : '未配置' }}
          </v-chip>
        </template>
        <template v-slot:item.actions="{ item }">
          <v-icon size="small" class="me-2" @click="openDialog(item)" color="primary">
            mdi-pencil
          </v-icon>
          <v-icon size="small" @click="confirmDelete(item)" color="error">
            mdi-delete
          </v-icon>
        </template>
      </v-data-table>
    </v-card>

    <!-- Dialog -->
    <v-dialog v-model="dialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ editingId ? '编辑模型' : '新增模型' }}</span>
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field v-model="formData.model_name" label="模型标识 (如: deepseek-chat)" required></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="formData.display_name" label="展示名称 (如: DeepSeek V3)" required></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-select
                  v-model="formData.model_type"
                  :items="modelTypeOptions"
                  item-title="title"
                  item-value="value"
                  label="模型用途"
                  required
                ></v-select>
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="formData.provider" label="供应商 (Provider)" required></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.endpoint"
                  label="Endpoint"
                  placeholder="FastDetect: https://api.fastdetect.net/api/detect；对话模型: /chat/completions"
                ></v-text-field>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.api_key"
                  :label="editingId ? 'API Key（留空则保持不变）' : 'API Key'"
                  :type="showApiKey ? 'text' : 'password'"
                  :append-inner-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                  placeholder="sk-..."
                  autocomplete="off"
                  @click:append-inner="showApiKey = !showApiKey"
                ></v-text-field>
              </v-col>
              <v-col cols="12" sm="6">
                <v-switch v-model="formData.is_active" label="是否开启" color="success" hide-details></v-switch>
              </v-col>
              <v-col cols="12">
                <v-textarea v-model="formData.description" label="模型描述" rows="3" auto-grow></v-textarea>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="blue-darken-1" variant="text" @click="save" :loading="saving">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirm -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title class="text-h5">确认删除?</v-card-title>
        <v-card-text>确定要删除模型 "{{ itemToDelete?.display_name }}" 吗?</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue-darken-1" variant="text" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" variant="text" @click="executeDelete" :loading="deleting">确定</v-btn>
          <v-spacer></v-spacer>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { getLLMModels, createLLMModel, updateLLMModel, deleteLLMModel } from '@/api/llm';
import type { LLMModel } from '@/api/llm';

const dialog = ref(false);
const deleteDialog = ref(false);
const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const showApiKey = ref(false);
const models = ref<LLMModel[]>([]);
const itemToDelete = ref<LLMModel | null>(null);

const editingId = ref<number | null>(null);
const formData = ref<Partial<LLMModel>>({
  model_name: '',
  display_name: '',
  provider: 'openai_compat',
  model_type: 'chat',
  endpoint: '',
  api_key: '',
  is_active: true,
  description: '',
});

const modelTypeOptions = [
  { title: '对话模型', value: 'chat' },
  { title: 'FastDetect AIGC 检测', value: 'fastdetect' },
];

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

const headers = [
  { title: '展示名称', align: 'start', key: 'display_name' },
  { title: '模型标识', key: 'model_name' },
  { title: '用途', key: 'model_type' },
  { title: '供应商', key: 'provider' },
  { title: 'API Key', key: 'has_api_key' },
  { title: '启用状态', key: 'is_active' },
  { title: '操作', key: 'actions', sortable: false, align: 'end' },
];

function modelTypeText(value?: string) {
  if (value === 'fastdetect') return 'FastDetect'
  return '对话模型'
}

async function fetchModels() {
  loading.value = true;
  try {
    const res = await getLLMModels();
    models.value = res.data || res;
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
}

function openDialog(item?: LLMModel) {
  if (item) {
    editingId.value = item.id;
    formData.value = { ...item, api_key: '' };
  } else {
    editingId.value = null;
    formData.value = {
      model_name: '',
      display_name: '',
      provider: 'openai_compat',
      model_type: 'chat',
      endpoint: '',
      api_key: '',
      is_active: true,
      description: '',
    };
  }
  showApiKey.value = false;
  dialog.value = true;
}

async function save() {
  saving.value = true;
  try {
    if (editingId.value) {
      await updateLLMModel(editingId.value, formData.value);
    } else {
      await createLLMModel(formData.value);
    }
    dialog.value = false;
    await fetchModels();
  } catch (err) {
    console.error(err);
  } finally {
    saving.value = false;
  }
}

function confirmDelete(item: LLMModel) {
  itemToDelete.value = item;
  deleteDialog.value = true;
}

async function executeDelete() {
  if (!itemToDelete.value) return;
  deleting.value = true;
  try {
    await deleteLLMModel(itemToDelete.value.id);
    deleteDialog.value = false;
    await fetchModels();
  } catch (err) {
    console.error(err);
  } finally {
    deleting.value = false;
  }
}

async function toggleActive(item: LLMModel) {
  try {
    await updateLLMModel(item.id, { is_active: item.is_active });
  } catch (err) {
    item.is_active = !item.is_active; // revert
    console.error(err);
  }
}

onMounted(() => {
  fetchModels();
});
</script>
