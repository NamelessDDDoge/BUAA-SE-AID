import http from './request'

export default {
  createResourceTask(data: {
    task_type: 'paper' | 'review'
    task_name?: string
    file_ids: number[]
    extract_images?: boolean
    if_use_llm?: boolean
    method_switches?: Record<string, boolean>
  }) {
    return http.post('/resource-task/create/', data)
  },

  getPaperResults(taskId: string | number) {
    return http.get(`/paper-results/${taskId}/`)
  },

  submitReviewRequest(data: {
    task_id: string | number
    reviewers: number[]
    selected_file_ids?: number[]
    reason?: string
  }) {
    return http.post('/create_resource_review_task_placeholder/', data)
  },
}
