import request from './request'

export interface LLMModel {
  id: number
  model_name: string
  display_name: string
  provider: string
  is_active: boolean
  description: string
}

export function getActiveLLMModels() {
  return request.get('/llms/active/')
}
