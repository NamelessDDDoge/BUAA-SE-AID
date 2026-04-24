<template>
  <div class="d-flex flex-column ga-4">
    <ResourceDetectionDetailStep
      :task="task"
      :reviewer-options="reviewerOptions"
      @download="emit('download')"
      @request-review="emit('request-review', $event)"
    />

    <v-card v-if="overallEvaluation" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-file-search-outline</v-icon>
        <span class="text-h6">Review 综合审查</span>
      </v-card-title>
      <v-card-text>
        <v-alert :type="overallAlertType" variant="tonal" class="mb-4">
          <div class="mb-1"><strong>模板化倾向：</strong>{{ levelText(overallEvaluation.template_like_level) }}</div>
          <div class="mb-1"><strong>内容错误风险：</strong>{{ levelText(overallEvaluation.wrongness_level) }}</div>
          <div class="mb-1"><strong>与论文相关度：</strong>{{ levelText(overallEvaluation.relevance_level) }}</div>
          <div><strong>总结：</strong>{{ overallEvaluation.summary || '暂无总结' }}</div>
        </v-alert>

        <div v-if="overallEvaluation.key_findings?.length" class="mb-3">
          <div class="text-subtitle-2 mb-2">关键发现</div>
          <v-chip
            v-for="(item, idx) in overallEvaluation.key_findings"
            :key="`finding-${idx}`"
            class="mr-2 mb-2"
            color="warning"
            variant="tonal"
            size="small"
          >
            {{ item }}
          </v-chip>
        </div>

        <div v-if="overallEvaluation.suggestions?.length">
          <div class="text-subtitle-2 mb-2">建议</div>
          <v-list density="compact">
            <v-list-item v-for="(item, idx) in overallEvaluation.suggestions" :key="`suggest-${idx}`">
              <v-list-item-title>{{ item }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>
    </v-card>

    <v-card v-if="paragraphAnalyses.length" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="indigo">mdi-format-list-text</v-icon>
        <span class="text-h6">Review 段落审查</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item
            v-for="(item, index) in paragraphAnalyses"
            :key="`review-para-${index}`"
            class="mb-4 pa-4 bg-grey-lighten-4 rounded-lg"
          >
            <template #prepend>
              <v-avatar :color="paragraphAvatarColor(item)" size="40" class="mr-4 text-white">
                {{ (item.review_paragraph_index ?? index) + 1 }}
              </v-avatar>
            </template>

            <v-list-item-title class="text-subtitle-1 font-weight-bold mb-2">
              第 {{ (item.review_paragraph_index ?? index) + 1 }} 段
              <v-chip size="small" class="ml-2" :color="levelColor(item.template_like_level)">
                模板化 {{ levelText(item.template_like_level) }}
              </v-chip>
              <v-chip size="small" class="ml-2" :color="levelColor(item.wrongness_level)">
                错误风险 {{ levelText(item.wrongness_level) }}
              </v-chip>
              <v-chip size="small" class="ml-2" color="primary" variant="tonal">
                相关度 {{ formatScore(item.relevance_score) }}
              </v-chip>
            </v-list-item-title>

            <v-list-item-subtitle class="text-body-1" style="white-space: pre-wrap;">
              <strong>Review 内容：</strong>{{ item.review_text || '-' }}
            </v-list-item-subtitle>

            <div class="mt-3">
              <v-alert type="info" variant="tonal" density="compact" class="text-body-2 mb-2">
                <strong>论文参考段落：</strong>
                {{ item.paper_paragraph_index !== null && item.paper_paragraph_index !== undefined ? `第 ${item.paper_paragraph_index + 1} 段` : '未匹配到明确段落' }}
              </v-alert>
              <v-alert type="warning" variant="tonal" density="compact" class="text-body-2">
                <strong>分析解释：</strong>{{ item.explanation || '暂无解释。' }}
              </v-alert>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card v-if="task?.results?.review_analysis_results?.overall?.summary || task?.results?.relevance_results?.length" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="teal">mdi-book-open-page-variant-outline</v-icon>
        <span class="text-h6">原始审查数据</span>
      </v-card-title>
      <v-card-text>
        <v-expansion-panels variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>Review 总体数据</v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="json-block">{{ task?.results?.review_analysis_results || task?.results?.overall_evaluation || {} }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel v-if="task?.results?.relevance_results?.length">
            <v-expansion-panel-title>段落明细</v-expansion-panel-title>
            <v-expansion-panel-text>
              <pre class="json-block">{{ task.results.relevance_results }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
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

const overallEvaluation = computed(() => props.task?.results?.review_analysis_results?.overall || props.task?.results?.overall_evaluation || null)
const paragraphAnalyses = computed(() => {
  const raw = props.task?.results?.review_analysis_results?.paragraph_results || props.task?.results?.relevance_results || []
  return Array.isArray(raw) ? raw.map((item: any) => ({
    review_paragraph_index: item.review_paragraph_index ?? item.paragraph_index,
    review_text: item.review_text ?? item.text,
    paper_paragraph_index: item.paper_paragraph_index,
    explanation: item.explanation ?? item.relevance_explanation,
    template_like_level: item.template_like_level ?? item.details?.template_like_level,
    wrongness_level: item.wrongness_level ?? item.details?.wrongness_level,
    relevance_score: item.relevance_score ?? item.details?.relevance_score,
    relevance_level: item.relevance_level ?? item.label,
  })) : []
})

const overallAlertType = computed(() => {
  const level = String(overallEvaluation.value?.relevance_level || overallEvaluation.value?.wrongness_level || 'low').toLowerCase()
  if (level === 'high') return 'error'
  if (level === 'medium') return 'warning'
  return 'success'
})

const levelText = (level?: string) => {
  const normalized = String(level || 'low').toLowerCase()
  if (normalized === 'high') return '高'
  if (normalized === 'medium') return '中'
  return '低'
}

const levelColor = (level?: string) => {
  const normalized = String(level || 'low').toLowerCase()
  if (normalized === 'high') return 'error'
  if (normalized === 'medium') return 'warning'
  return 'success'
}

const paragraphAvatarColor = (item: any) => {
  if (String(item.template_like_level || '').toLowerCase() === 'high' || String(item.wrongness_level || '').toLowerCase() === 'high') {
    return 'error'
  }
  if (String(item.relevance_level || '').toLowerCase() === 'medium') {
    return 'warning'
  }
  return 'primary'
}

const formatScore = (value: any) => {
  const numberValue = Number(value || 0)
  return `${Math.round(numberValue * 1000) / 10}%`
}
</script>

<style scoped>
.json-block {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  background: rgb(var(--v-theme-surface-variant));
  padding: 12px;
  border-radius: 8px;
}
</style>
