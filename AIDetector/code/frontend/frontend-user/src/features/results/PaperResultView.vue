<template>
  <div class="d-flex flex-column ga-4">
    <ResourceDetectionDetailStep :task="task" :reviewer-options="reviewerOptions" @download="emit('download')" @request-review="emit('request-review', $event)" />

    <v-card v-if="overallEvaluation" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-file-chart-outline</v-icon>
        <span class="text-h6">整篇论文综合评价</span>
      </v-card-title>
      <v-card-text>
        <v-alert :type="overallRiskType" variant="tonal" class="mb-4">
          <div class="mb-1"><strong>风险等级：</strong>{{ overallRiskText }}</div>
          <div class="mb-1"><strong>风险评分：</strong>{{ Number(overallEvaluation.risk_score || 0) }}</div>
          <div><strong>总结：</strong>{{ overallEvaluation.summary || '暂无总结' }}</div>
        </v-alert>

        <div v-if="(overallEvaluation.key_concerns || []).length" class="mb-3">
          <div class="text-subtitle-2 mb-2">关键关注点</div>
          <v-chip
            v-for="(item, idx) in overallEvaluation.key_concerns"
            :key="`concern-${idx}`"
            size="small"
            color="warning"
            variant="tonal"
            class="mr-2 mb-2"
          >
            {{ item }}
          </v-chip>
        </div>

        <div v-if="(overallEvaluation.suggestions || []).length">
          <div class="text-subtitle-2 mb-2">建议</div>
          <v-list density="compact">
            <v-list-item v-for="(item, idx) in overallEvaluation.suggestions" :key="`suggest-${idx}`">
              <v-list-item-title>{{ item }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>
    </v-card>

    <v-card v-if="confirmedParagraphs.length" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="deep-orange">mdi-alert-decagram-outline</v-icon>
        <span class="text-h6">基本确认 AI 段落</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="two">
          <v-list-item v-for="(item, idx) in confirmedParagraphs" :key="`confirmed-${idx}`">
            <v-list-item-title>
              第 {{ (item.paragraph_index ?? 0) + 1 }} 段 · AIGC率 {{ ((item.probability || 0) * 100).toFixed(1) }}%
            </v-list-item-title>
            <v-list-item-subtitle>{{ item.reason || '该段达到确认阈值。' }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card v-if="referenceResults.length" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="indigo">mdi-book-search-outline</v-icon>
        <span class="text-h6">参考文献真实性分析</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item v-for="(refItem, idx) in referenceResults" :key="`ref-${idx}`" class="mb-2">
            <v-list-item-title>
              [{{ (refItem.reference_index ?? 0) + 1 }}]
              <v-chip size="x-small" class="ml-2" :color="referenceLabelColor(refItem.authenticity_label)">
                {{ refItem.authenticity_label || 'unknown' }}
              </v-chip>
              <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">
                真实性分 {{ Number(refItem.authenticity_score || 0).toFixed(2) }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle style="white-space: pre-wrap;">{{ refItem.reference }}</v-list-item-subtitle>
            <div class="text-caption text-medium-emphasis mt-1">{{ refItem.authenticity_reason || '暂无说明' }}</div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card v-if="dataAuthenticity" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="teal">mdi-chart-bell-curve-cumulative</v-icon>
        <span class="text-h6">数据真实性分析</span>
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-3">
          {{ dataAuthenticity.summary || '暂无数据真实性摘要。' }}
        </v-alert>
        <v-list v-if="(dataAuthenticity.findings || []).length" lines="two">
          <v-list-item v-for="(finding, idx) in dataAuthenticity.findings" :key="`finding-${idx}`" class="mb-2">
            <v-list-item-title>
              第 {{ (finding.paragraph_index ?? 0) + 1 }} 段
              <v-chip size="x-small" class="ml-2" :color="riskLevelColor(finding.risk_level)">
                {{ finding.risk_level || 'unknown' }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>{{ finding.claim_text || '-' }}</v-list-item-subtitle>
            <div class="text-caption text-medium-emphasis mt-1">{{ finding.reason || '-' }}</div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
    
    <!-- 论文段落检测结果展示 -->
    <v-card v-if="task?.results?.paragraph_results?.length" class="mt-4" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-text-box-search-outline</v-icon>
        <span class="text-h6">论文段落检测结果</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item v-for="(para, index) in task.results.paragraph_results" :key="index" class="mb-4 pa-4 bg-grey-lighten-4 rounded-lg">
            <template #prepend>
              <v-avatar :color="para.label === 'suspicious' ? 'error' : 'success'" size="40" class="mr-4 text-white">
                {{ para.paragraph_index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="text-subtitle-1 font-weight-bold mb-2">
              检测结果: {{ para.label === 'suspicious' ? '疑似 AI 生成' : '正常' }} 
              <v-chip size="small" :color="para.label === 'suspicious' ? 'error' : 'success'" class="ml-2">
                概率: {{ (para.probability * 100).toFixed(1) }}%
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle class="text-body-1" style="white-space: pre-wrap;">
              {{ para.text }}
            </v-list-item-subtitle>
            
            <div v-if="para.label === 'suspicious'" class="mt-3">
              <v-alert type="warning" variant="tonal" density="compact" class="text-body-2">
                <strong>可疑分析:</strong> {{ getExplanation(para.paragraph_index) || '该段落具有较高的 AI 生成特征。' }}
              </v-alert>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ResourceDetectionDetailStep from '@/components/steps/ResourceDetectionDetailStep.vue'

const props = defineProps<{
  task: any
  reviewerOptions: Array<{ id: number; username: string; avatar?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[] }): void
}>()

const overallEvaluation = computed(() => props.task?.results?.overall_evaluation || null)
const confirmedParagraphs = computed(() => props.task?.results?.confirmed_ai_paragraphs || [])
const referenceResults = computed(() => props.task?.results?.reference_results || [])
const dataAuthenticity = computed(() => props.task?.results?.data_authenticity_results || null)

const overallRiskType = computed(() => {
  const level = String(overallEvaluation.value?.risk_level || '').toLowerCase()
  if (level === 'high') return 'error'
  if (level === 'medium') return 'warning'
  return 'success'
})

const overallRiskText = computed(() => {
  const level = String(overallEvaluation.value?.risk_level || '').toLowerCase()
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  return '未知'
})

const referenceLabelColor = (label?: string) => {
  if (label === 'high_risk' || label === 'missing') return 'error'
  if (label === 'uncertain') return 'warning'
  if (label === 'likely_authentic') return 'success'
  return 'grey'
}

const riskLevelColor = (level?: string) => {
  if (level === 'high') return 'error'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'success'
  return 'grey'
}

const getExplanation = (index: number) => {
  const suspicious = props.task?.results?.suspicious_paragraphs || []
  const match = suspicious.find((s: any) => s.paragraph_index === index)
  return match ? match.explanation : ''
}
</script>
