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

    <!-- 论文段落检测结果展示 -->
    <v-card v-if="task?.results?.paragraph_results?.length" elevation="2" rounded="lg">
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

    <v-card v-if="showDataAuthenticity" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="teal">mdi-table-search</v-icon>
        <span class="text-h6">论文数据真实性分析</span>
      </v-card-title>
      <v-card-text>
        <v-alert :type="dataAuthenticityAlertType" variant="tonal" class="mb-4">
          <div class="d-flex align-center flex-wrap ga-2 mb-1">
            <strong>分析摘要：</strong>
            <v-chip size="x-small" color="primary" variant="tonal">{{ dataSummarySourceText }}</v-chip>
          </div>
          <div class="mb-1">{{ dataAuthenticitySummary }}</div>
          <div class="text-caption">
            已识别表格 {{ documentTableCount }} 个 · 已分析表格 {{ tableResults.length }} 个 · 可疑点 {{ dataFindings.length }} 个
          </div>
        </v-alert>

        <div v-if="dataSummaryKeyPoints.length" class="mb-4">
          <div class="text-subtitle-2 mb-2">摘要依据</div>
          <v-chip
            v-for="(item, idx) in dataSummaryKeyPoints"
            :key="`data-key-point-${idx}`"
            size="small"
            color="teal"
            variant="tonal"
            class="mr-2 mb-2"
          >
            {{ item }}
          </v-chip>
        </div>

        <div v-if="dataFindings.length" class="mb-4">
          <div class="text-subtitle-2 mb-2">可疑数据证据</div>
          <v-list lines="three">
            <v-list-item v-for="(item, idx) in dataFindings" :key="`data-finding-${idx}`" class="mb-2">
              <v-list-item-title class="d-flex align-center flex-wrap ga-2">
                <v-chip size="x-small" :color="dataRiskColor(item.risk_level)">
                  {{ riskLevelText(item.risk_level) }}
                </v-chip>
                <span>{{ findingSourceText(item) }}</span>
              </v-list-item-title>
              <v-list-item-subtitle style="white-space: pre-wrap;">
                {{ item.claim_text || item.evidence || '暂无证据文本' }}
              </v-list-item-subtitle>
              <div class="text-caption text-medium-emphasis mt-1">{{ item.reason || '暂无说明' }}</div>
            </v-list-item>
          </v-list>
        </div>

        <div v-if="tableResults.length">
          <div class="text-subtitle-2 mb-2">表格分析结果</div>
          <v-list lines="two">
            <v-list-item v-for="(item, idx) in tableResults" :key="`table-result-${idx}`" class="mb-2">
              <v-list-item-title class="d-flex align-center flex-wrap ga-2">
                <span>表格 {{ Number(item.table_index ?? idx) + 1 }}</span>
                <v-chip size="x-small" :color="dataRiskColor(item.risk_level)">
                  {{ riskLevelText(item.risk_level) }}
                </v-chip>
                <v-chip v-if="item.page_number" size="x-small" color="primary" variant="tonal">
                  第 {{ item.page_number }} 页
                </v-chip>
                <v-chip v-if="item.source" size="x-small" color="grey" variant="tonal">
                  {{ tableSourceText(item.source) }}
                </v-chip>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ tableShapeText(item) }} · {{ item.reason || '暂无说明' }}
              </v-list-item-subtitle>
              <div v-if="item.evidence_summary" class="text-caption text-medium-emphasis mt-1">
                证据摘要：{{ item.evidence_summary }}
              </div>
              <div v-if="(item.suspicious_cells || []).length" class="mt-2">
                <v-chip
                  v-for="(cell, cellIdx) in item.suspicious_cells"
                  :key="`table-${idx}-cell-${cellIdx}`"
                  size="x-small"
                  color="warning"
                  variant="tonal"
                  class="mr-1 mb-1"
                >
                  {{ cell }}
                </v-chip>
              </div>
              <div v-if="hasTablePreview(item)" class="mt-3 table-preview-wrap">
                <div class="text-caption font-weight-medium mb-1">已提取表头与表项预览</div>
                <v-table density="compact" class="table-preview rounded-lg">
                  <thead v-if="tableHeaders(item).length">
                    <tr>
                      <th v-for="(header, headerIdx) in tableHeaders(item)" :key="`table-${idx}-header-${headerIdx}`">
                        {{ header || `列 ${headerIdx + 1}` }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIdx) in tableRowsPreview(item)" :key="`table-${idx}-row-${rowIdx}`">
                      <td v-for="(cell, cellIdx) in normalizePreviewRow(row, item)" :key="`table-${idx}-row-${rowIdx}-cell-${cellIdx}`">
                        {{ cell || '-' }}
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </div>
            </v-list-item>
          </v-list>
        </div>

        <v-alert v-else-if="!dataFindings.length" type="info" variant="tonal" density="compact">
          暂无可展示的表格级结果；如果摘要显示未能调用 LLM，请检查模型配置或额度状态。
        </v-alert>
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
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[]; reason: string }): void
}>()

const overallEvaluation = computed(() => props.task?.results?.overall_evaluation || null)
const confirmedParagraphs = computed(() => props.task?.results?.confirmed_ai_paragraphs || [])
const referenceResults = computed(() => props.task?.results?.reference_results || [])
const dataAuthenticityResults = computed(() => props.task?.results?.data_authenticity_results || null)
const dataFindings = computed(() => dataAuthenticityResults.value?.findings || [])
const tableResults = computed(() => props.task?.results?.table_results || dataAuthenticityResults.value?.table_results || [])
const documentTableCount = computed(() => Number(props.task?.results?.document?.table_count || tableResults.value.length || 0))
const dataSummaryKeyPoints = computed(() => dataAuthenticityResults.value?.summary_key_points || [])

const showDataAuthenticity = computed(() => dataAuthenticityResults.value?.enabled === true)

const dataAuthenticitySummary = computed(() => {
  const summary = String(dataAuthenticityResults.value?.summary || '').trim()
  if (summary && summary !== '-') return summary
  if (documentTableCount.value > 0) return '已识别论文中的表格/数据内容，暂无明确风险摘要。'
  return '暂无数据真实性分析结果。'
})

const dataAuthenticityAlertType = computed(() => {
  const summary = dataAuthenticitySummary.value
  if (summary.includes('失败') || summary.includes('未能')) return 'warning'
  if (dataFindings.value.some((item: any) => item.risk_level === 'high')) return 'error'
  if (dataFindings.value.some((item: any) => item.risk_level === 'medium')) return 'warning'
  return dataFindings.value.length ? 'info' : 'success'
})

const dataSummarySourceText = computed(() => {
  if (dataAuthenticityResults.value?.summary_source === 'llm') return 'LLM 生成'
  if (dataAuthenticityResults.value?.summary_source === 'rule_based') return '规则兜底'
  return '系统摘要'
})

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

const dataRiskColor = (level?: string) => {
  if (level === 'high') return 'error'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'info'
  if (level === 'none') return 'success'
  return 'grey'
}

const riskLevelText = (level?: string) => {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  if (level === 'none') return '未见风险'
  return '未知'
}

const findingSourceText = (item: any) => {
  if (item?.source_type === 'table') return `表格 ${Number(item.table_index ?? 0) + 1}`
  if (item?.source_type === 'paragraph') return `第 ${Number(item.paragraph_index ?? 0) + 1} 段`
  return '数据证据'
}

const tableSourceText = (source?: string) => {
  if (source === 'pdf_native') return 'PDF 原生表格'
  if (source === 'pdf_inferred') return 'PDF 推断表格'
  if (source === 'docx') return 'Word 表格'
  if (source === 'text') return '文本表格'
  return source || '未知来源'
}

const tableShapeText = (item: any) => {
  const rows = Number(item?.row_count || 0)
  const columns = Number(item?.column_count || 0)
  if (rows && columns) return `${rows} 行 × ${columns} 列`
  if (rows) return `${rows} 行`
  if (columns) return `${columns} 列`
  return '结构信息不足'
}

const tableHeaders = (item: any) => {
  return Array.isArray(item?.headers) ? item.headers.map((cell: any) => String(cell ?? '')) : []
}

const tableRowsPreview = (item: any) => {
  if (Array.isArray(item?.rows_preview)) return item.rows_preview.slice(0, 5)
  if (Array.isArray(item?.rows)) return item.rows.slice(0, 5)
  return []
}

const hasTablePreview = (item: any) => {
  return tableHeaders(item).length > 0 || tableRowsPreview(item).length > 0
}

const normalizePreviewRow = (row: any, item: any) => {
  const cells = Array.isArray(row) ? row.map((cell: any) => String(cell ?? '')) : [String(row ?? '')]
  const columnCount = Math.max(tableHeaders(item).length, cells.length)
  return cells.concat(Array(Math.max(0, columnCount - cells.length)).fill(''))
}

const getExplanation = (index: number) => {
  const suspicious = props.task?.results?.suspicious_paragraphs || []
  const match = suspicious.find((s: any) => s.paragraph_index === index)
  return match ? match.explanation : ''
}
</script>

<style scoped>
.table-preview-wrap {
  overflow-x: auto;
}

.table-preview {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  min-width: 520px;
}

.table-preview :deep(th),
.table-preview :deep(td) {
  max-width: 220px;
  white-space: normal;
  word-break: break-word;
}
</style>
