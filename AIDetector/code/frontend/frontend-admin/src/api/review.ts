import http from './request'

export default {
    getReviewRequests(params: any) {
        return http.get('/get_reviewRequest/all/', { params })
    },
    // 获取审核请求详情
    getReviewRequestDetails(id: number, request_type: 'image' | 'resource' = 'image') {
        return http.get(`/get_reviewRequest/${id}/`, { params: { request_type } })
    },

    // 处理审核请求
    handleReviewRequest(id: number, data: any) {
        return http.post(`/handle_reviewRequest/${id}/`, data)
    },

    getResourceTextPreview(fileId: number, taskId?: number | string | null) {
        return http.get(`/upload/${fileId}/preview_text/`, {
            params: taskId ? { task_id: taskId } : undefined,
        })
    },

    downloadTaskReportAdmin(taskId: number) {
        return http.get(`/admin/tasks/${taskId}/report/`, { responseType: 'blob' })
    }
}
