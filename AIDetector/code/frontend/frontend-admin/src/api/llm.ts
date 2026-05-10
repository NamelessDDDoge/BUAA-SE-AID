import request from './request'

export interface LLMModel {
  id: number
  model_name: string
  display_name: string
  provider: string
  is_active: boolean
  description: string
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
