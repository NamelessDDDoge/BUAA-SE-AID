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
          <div class="mb-1"><strong>综合结论：</strong>{{ qualificationText }}</div>
          <div v-if="qualificationReason" class="mb-1"><strong>判定原因：</strong>{{ qualificationReason }}</div>
          <div class="mb-1"><strong>模板化倾向：</strong>{{ riskLevelText(overallEvaluation.template_like_level) }}</div>
          <div class="mb-1"><strong>内容错误风险：</strong>{{ riskLevelText(overallEvaluation.wrongness_level) }}</div>
          <div class="mb-1"><strong>与论文相关度：</strong>{{ relevanceLevelText(overallEvaluation.relevance_level) }}</div>
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
              <v-chip size="small" class="ml-2" :color="riskLevelColor(item.template_like_level)">
                模板化 {{ riskLevelText(item.template_like_level) }}
              </v-chip>
              <v-chip size="small" class="ml-2" :color="riskLevelColor(item.wrongness_level)">
                错误风险 {{ riskLevelText(item.wrongness_level) }}
              </v-chip>
              <v-chip size="small" class="ml-2" :color="relevanceLevelColor(item.relevance_level)" variant="tonal">
                相关度 {{ relevanceLevelText(item.relevance_level) }}
              </v-chip>
              <v-chip size="small" class="ml-2" color="primary" variant="tonal">
                匹配分数 {{ formatScore(item.relevance_score) }}
              </v-chip>
            </v-list-item-title>

            <div class="text-body-1 review-paragraph-text">
              <strong>Review 内容：</strong>{{ item.review_text || '-' }}
            </div>

            <div class="mt-3">
              <v-alert :type="relevanceAlertType(item.relevance_level)" variant="tonal" density="compact" class="text-body-2 mb-2">
                <strong>论文参考段落：</strong>
                {{ item.paper_paragraph_index !== null && item.paper_paragraph_index !== undefined ? `第 ${item.paper_paragraph_index + 1} 段` : '未匹配到明确段落' }}
              </v-alert>
              <v-alert :type="paragraphExplanationAlertType(item)" variant="tonal" density="compact" class="text-body-2">
                <strong>分析解释：</strong>{{ item.explanation || '暂无解释。' }}
              </v-alert>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card v-if="reviewItems.length > 1" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="teal">mdi-file-multiple-outline</v-icon>
        <span class="text-h6">批量 Review 结果总览</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item v-for="(item, idx) in reviewItems" :key="`review-item-${idx}`" class="mb-3">
            <v-list-item-title>
              {{ item.document?.review_file_name || `Review 资源 ${idx + 1}` }}
              <v-chip size="x-small" class="ml-2" color="primary" variant="tonal">
                论文 {{ item.document?.paper_file_name || '-' }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              段落 {{ (item.paragraph_results || []).length }}
              · 可疑 {{ countSuspicious(item.paragraph_results) }}
              · 相关项 {{ (item.relevance_results || []).length }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-card v-if="reviewItems.length > 1" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-tab-search</v-icon>
        <span class="text-h6">按资源查看 Review 结果</span>
      </v-card-title>
      <v-card-text>
        <v-chip-group v-model="selectedReviewItemIndex" selected-class="text-primary" class="mb-4" mandatory>
          <v-chip
            v-for="(item, idx) in reviewItems"
            :key="`review-switch-${idx}`"
            filter
            variant="outlined"
            color="primary"
          >
            {{ item.document?.review_file_name || `Review ${idx + 1}` }}
          </v-chip>
        </v-chip-group>

        <v-window v-model="selectedReviewItemIndex">
          <v-window-item v-for="(item, idx) in reviewItems" :key="`review-window-${idx}`" :value="idx">
            <v-alert type="info" variant="tonal" class="mb-4">
              <div><strong>评审文件：</strong>{{ item.document?.review_file_name || `Review ${idx + 1}` }}</div>
              <div><strong>论文文件：</strong>{{ item.document?.paper_file_name || '-' }}</div>
              <div><strong>段落数：</strong>{{ item.document?.review_paragraph_count ?? (item.paragraph_results || []).length }}</div>
            </v-alert>

            <v-list v-if="(item.paragraph_results || []).length" lines="three">
              <v-list-item
                v-for="(para, paraIndex) in item.paragraph_results"
                :key="`review-item-${idx}-para-${paraIndex}`"
                class="mb-4 pa-4 bg-grey-lighten-4 rounded-lg"
              >
                <template #prepend>
                  <v-avatar :color="para.label === 'suspicious' ? 'error' : 'success'" size="40" class="mr-4 text-white">
                    {{ (para.paragraph_index ?? paraIndex) + 1 }}
                  </v-avatar>
                </template>
                <v-list-item-title class="text-subtitle-1 font-weight-bold mb-2">
                  检测结果: {{ para.label === 'suspicious' ? '疑似异常' : '正常' }}
                  <v-chip size="small" :color="para.label === 'suspicious' ? 'error' : 'success'" class="ml-2">
                    概率: {{ ((para.probability || 0) * 100).toFixed(1) }}%
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle class="text-body-1 review-paragraph-text">
                  {{ para.text }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <div v-else class="text-medium-emphasis py-4">当前资源暂无 Review 段落结果。</div>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ResourceDetectionDetailStep from '@/components/steps/ResourceDetectionDetailStep.vue'

const props = defineProps<{
  task: any
  reviewerOptions: Array<{ id: number; username: string; avatar?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[]; reason: string }): void
}>()

const overallEvaluation = computed(() => props.task?.results?.review_analysis_results?.overall || props.task?.results?.overall_evaluation || null)
const reviewItems = computed(() => Array.isArray(props.task?.results?.items) ? props.task.results.items : [])
const selectedReviewItemIndex = ref(0)

const paragraphAnalyses = computed(() => {
  const results = props.task?.results || {}
  const analysisRows = asArray(results.review_analysis_results?.paragraph_results)
  const relevanceRows = asArray(results.relevance_results)
  const paragraphRows = asArray(results.paragraph_results)
  const analysisByIndex = buildReviewIndexMap(analysisRows)
  const relevanceByIndex = buildReviewIndexMap(relevanceRows)
  const paragraphByIndex = buildReviewIndexMap(paragraphRows)
  const indexes = Array.from(new Set([
    ...analysisByIndex.keys(),
    ...relevanceByIndex.keys(),
    ...paragraphByIndex.keys(),
  ])).sort((a, b) => a - b)

  return indexes.map((reviewIndex) => {
    const analysisItem = analysisByIndex.get(reviewIndex) || {}
    const relevanceItem = relevanceByIndex.get(reviewIndex) || {}
    const paragraphItem = paragraphByIndex.get(reviewIndex) || {}

    return {
      review_paragraph_index: reviewIndex,
      review_text: firstPresent(
        analysisItem.review_text,
        analysisItem.text,
        relevanceItem.review_text,
        relevanceItem.text,
        paragraphItem.review_text,
        paragraphItem.text,
        paragraphItem.details?.review_text,
      ),
      paper_paragraph_index: firstPresent(
        analysisItem.paper_paragraph_index,
        relevanceItem.paper_paragraph_index,
        paragraphItem.paper_paragraph_index,
        paragraphItem.details?.paper_paragraph_index,
      ),
      paper_text: firstPresent(
        analysisItem.paper_text,
        relevanceItem.paper_text,
        paragraphItem.paper_text,
        paragraphItem.details?.paper_text,
      ),
      explanation: firstPresent(
        analysisItem.explanation,
        analysisItem.relevance_explanation,
        relevanceItem.explanation,
        relevanceItem.relevance_explanation,
        paragraphItem.explanation,
        paragraphItem.relevance_explanation,
        paragraphItem.details?.explanation,
        paragraphItem.details?.relevance_explanation,
      ),
      template_like_level: firstPresent(
        analysisItem.template_like_level,
        analysisItem.details?.template_like_level,
        relevanceItem.template_like_level,
        relevanceItem.details?.template_like_level,
        paragraphItem.template_like_level,
        paragraphItem.details?.template_like_level,
      ),
      wrongness_level: firstPresent(
        analysisItem.wrongness_level,
        analysisItem.details?.wrongness_level,
        relevanceItem.wrongness_level,
        relevanceItem.details?.wrongness_level,
        paragraphItem.wrongness_level,
        paragraphItem.details?.wrongness_level,
      ),
      relevance_score: firstPresent(
        analysisItem.relevance_score,
        analysisItem.details?.relevance_score,
        relevanceItem.relevance_score,
        relevanceItem.details?.relevance_score,
        paragraphItem.relevance_score,
        paragraphItem.details?.relevance_score,
      ),
      relevance_level: firstPresent(
        analysisItem.relevance_level,
        analysisItem.details?.relevance_level,
        relevanceItem.relevance_level,
        relevanceItem.label,
        relevanceItem.details?.relevance_level,
        paragraphItem.relevance_level,
        paragraphItem.details?.relevance_level,
      ),
    }
  })
})

const asArray = (value: any) => Array.isArray(value) ? value : []

const firstPresent = (...values: any[]) => values.find((value) => {
  if (typeof value === 'string') return value.trim() !== ''
  return value !== undefined && value !== null
})

const getReviewIndex = (item: any, fallbackIndex: number) => {
  const rawIndex = item?.review_paragraph_index ?? item?.paragraph_index ?? fallbackIndex
  const numberIndex = Number(rawIndex)
  return Number.isFinite(numberIndex) ? numberIndex : fallbackIndex
}

const buildReviewIndexMap = (items: any[]) => {
  const indexed = new Map<number, any>()
  items.forEach((item, index) => {
    const reviewIndex = getReviewIndex(item, index)
    if (!indexed.has(reviewIndex)) {
      indexed.set(reviewIndex, item)
    }
  })
  return indexed
}

const normalizeLevel = (level?: string) => String(level || '').toLowerCase()

const inferQualificationLabel = (overall?: any) => {
  const explicitLabel = String(overall?.qualification_label || '').toLowerCase()
  if (['qualified', 'attention', 'unqualified', 'unavailable'].includes(explicitLabel)) {
    return explicitLabel
  }
  const templateLevel = normalizeLevel(overall?.template_like_level)
  const wrongnessLevel = normalizeLevel(overall?.wrongness_level)
  const relevanceLevel = normalizeLevel(overall?.relevance_level)
  if (overall?.source === 'api_unavailable') return 'unavailable'
  if (templateLevel === 'high' || wrongnessLevel === 'high') return 'unqualified'
  if (relevanceLevel === 'low' || relevanceLevel === 'weak_match') return 'unqualified'
  if (templateLevel === 'medium' || wrongnessLevel === 'medium' || relevanceLevel === 'medium') return 'attention'
  if (templateLevel === 'unknown' || wrongnessLevel === 'unknown' || relevanceLevel === 'unknown') return 'attention'
  return 'qualified'
}

const qualificationLabel = computed(() => inferQualificationLabel(overallEvaluation.value))

const qualificationText = computed(() => {
  if (overallEvaluation.value?.qualification_text) return overallEvaluation.value.qualification_text
  if (qualificationLabel.value === 'qualified') return '合格'
  if (qualificationLabel.value === 'attention') return '需关注'
  if (qualificationLabel.value === 'unqualified') return '不合格'
  if (qualificationLabel.value === 'unavailable') return '分析不可用'
  return '未知'
})

const qualificationReason = computed(() => overallEvaluation.value?.qualification_reason || '')

const overallAlertType = computed(() => {
  if (qualificationLabel.value === 'unqualified') return 'error'
  if (qualificationLabel.value === 'attention') return 'warning'
  if (qualificationLabel.value === 'unavailable') return 'info'
  return 'success'
})

const riskLevelText = (level?: string) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high') return '高'
  if (normalized === 'medium') return '中'
  if (normalized === 'low') return '低'
  return '未知'
}

const relevanceLevelText = (level?: string) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high' || normalized === 'relevant') return '高'
  if (normalized === 'medium') return '中'
  if (normalized === 'low' || normalized === 'weak_match') return '低'
  return '未知'
}

const riskLevelColor = (level?: string) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high') return 'error'
  if (normalized === 'medium') return 'warning'
  if (normalized === 'low') return 'success'
  return 'grey'
}

const relevanceLevelColor = (level?: string) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high' || normalized === 'relevant') return 'success'
  if (normalized === 'medium') return 'warning'
  if (normalized === 'low' || normalized === 'weak_match') return 'grey'
  return 'grey'
}

const paragraphAvatarColor = (item: any) => {
  if (
    normalizeLevel(item.template_like_level) === 'high'
    || normalizeLevel(item.wrongness_level) === 'high'
    || normalizeLevel(item.relevance_level) === 'low'
    || normalizeLevel(item.relevance_level) === 'weak_match'
  ) {
    return 'error'
  }
  if (
    normalizeLevel(item.template_like_level) === 'medium'
    || normalizeLevel(item.wrongness_level) === 'medium'
    || normalizeLevel(item.relevance_level) === 'medium'
  ) {
    return 'warning'
  }
  return 'success'
}

const countSuspicious = (paragraphs?: any[]) => {
  if (!Array.isArray(paragraphs)) return 0
  return paragraphs.filter(item => item?.label === 'suspicious').length
}

const relevanceAlertType = (level?: string) => {
  const normalized = normalizeLevel(level)
  if (normalized === 'high' || normalized === 'relevant') return 'success'
  if (normalized === 'medium') return 'warning'
  return 'info'
}

const paragraphExplanationAlertType = (item: any) => {
  if (
    normalizeLevel(item.template_like_level) === 'high'
    || normalizeLevel(item.wrongness_level) === 'high'
    || normalizeLevel(item.relevance_level) === 'low'
    || normalizeLevel(item.relevance_level) === 'weak_match'
  ) {
    return 'error'
  }
  if (
    normalizeLevel(item.template_like_level) === 'medium'
    || normalizeLevel(item.wrongness_level) === 'medium'
    || normalizeLevel(item.relevance_level) === 'medium'
  ) {
    return 'warning'
  }
  return 'info'
}

const formatScore = (value: any) => {
  const numberValue = Number(value || 0)
  return `${Math.round(numberValue * 1000) / 10}%`
}
</script>

<style scoped>
.review-paragraph-text {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
