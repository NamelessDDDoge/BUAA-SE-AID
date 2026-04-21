import http from './request'

export default {
    getReviewRequests(params: any)  {
        return http.get('/get_reviewRequest/all/',{ params })
    },
     // 获取审核请求详情
     getReviewRequestDetails(id: number) {
        return http.get(`/get_reviewRequest/${id}/`)
    },

    // 处理审核请求
    handleReviewRequest(id: number, data: any) {
        return http.post(`/handle_reviewRequest/${id}/`, data)
    }
}
