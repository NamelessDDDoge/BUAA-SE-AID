import request from './request'

export interface LLMModel {
  id: number
  model_name: string
  display_name: string
  provider: string
  model_type: 'chat' | 'fastdetect'
  endpoint?: string
  api_key?: string
  has_api_key?: boolean
  is_active: boolean
  description: string
  health_status?: 'unknown' | 'available' | 'exhausted' | 'invalid' | 'error'
  health_detail?: string
  health_checked_at?: string
  credit_used?: number | null
  credit_total?: number | null
  created_at: string
  updated_at: string
}

export function getLLMModels() {
  return request.get('/admin/llms/')
}

export function createLLMModel(data: Partial<LLMModel>) {
  return request.post('/admin/llms/', data)
}

export function updateLLMModel(id: number, data: Partial<LLMModel>) {
  return request.patch(`/admin/llms/${id}/`, data)
}

export function deleteLLMModel(id: number) {
  return request.delete(`/admin/llms/${id}/`)
}
