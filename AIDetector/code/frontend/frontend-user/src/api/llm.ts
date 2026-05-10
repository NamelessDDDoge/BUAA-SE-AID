import request from './request'

export interface LLMModel {
  id: number
  model_name: string
  display_name: string
  provider: string
  model_type?: 'chat' | 'fastdetect'
  endpoint?: string
  has_api_key?: boolean
  is_active: boolean
  description: string
}

export function getActiveLLMModels() {
  return request.get('/llms/active/')
}
