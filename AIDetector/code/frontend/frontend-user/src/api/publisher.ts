import http from './request'

export default {
  //发布审核任务
  dispatchAnnual(data: any) {
    return http.post('/create_review_task_with_admin_check/', data)
  },

  //data是taskId
  //返回某个task的所有人工审核任务的完成情况，只返回百分比
  getAllAnnual(data: any) {
    return http.get(`/get_task_completion_status/${data}`)
  },

  //返回某个task的所有images和所有人工审核的结果
  getAnnualDetail(data: any) {
    return http.get(`/get_task_detail/${data}/`)
  },

  //返回特定审核员对特定任务的审核结果
  getReviewerDetail(data: any) {
    return http.get(`/get_task_reviewer_detail/${data.taskId}/${data.reviewer_id}`)
  },

  getAllReviewers() {
    return http.get('/get_all_reviewers/')
  },

  getReviewers(data: any) {
    return http.get(`publishers/${data.publisher_id}/reviewers/`)
  },

  //获取某个出版社所有检测的任务
  getAllDetectionTask(data: any) {
    return http.get('/user-tasks/', { params: data })
  },

  //提交AI检测任务
  submitDetection(data: any) {
    return http.post('/detection/submit/', data)
  },

  createResourceTask(data: {
    task_type: 'paper' | 'review'
    task_name?: string
    file_ids: number[]
  }) {
    return http.post('/resource-task/create/', data)
  },

  //获取某个任务的所有图片的AI检测结果
  getTaskResults(data: any) {
    return http.get(`/tasks/${data}/results/`)
  },

  getFakeImage(data: any) {
    return http.get(`/tasks/${data.task_id}/fake_results/?include_image=${data.include_image}`)
  },

  getNormalImage(data: any) {
    return http.get(`/tasks/${data.task_id}/normal_results/?include_image=${data.include_image}`,)
  },

  getSingleImageResult(data: any) {
    return http.get(`/results/${data}/`)
  },

  getDetectionTaskDetail(data: { task_id: string | number }) {
    return http.get(`/detection-task/${data.task_id}/status/`)
  },

  submitResourceReviewRequest(data: {
    task_id: string | number
    reviewers: number[]
    selected_file_ids?: number[]
    reason?: string
  }) {
    return http.post('/create_resource_review_task_placeholder/', data)
  },

  downloadReport(data: any) {
    return http.get(`/tasks/${data}/report/`, {
      responseType: 'blob'
    })
  },

  downloadReviewReport(data: any) {
    return http.get(`/manual-review/${data.review_request_id}/report/`, {
      responseType: 'blob'
    })
  },

  getPublisherReviewTasks(params: {
    page?: number
    page_size?: number
    status?: string
    startTime?: string
    endTime?: string
  }) {
    return http.get('/get_publisher_review_tasks/', { params })
  },

  getTaskSummary() {
    return http.get('/task-summary/')
  },

  ifHasPermission(params: {
    task_id: string
  }) {
    return http.get(`/publisher-dectectiontask-access/`, { params })
  },

  //publisher端返回人工审核表头
  getRequestDetail(data: any) {
    return http.get(`/get_request_detail/${data.review_request_id}/`)
  },

  //publisher获取单个图片的所有人工审核结果
  getImageReviewAll(data: any) {
    return http.get(`/get_img_review_all/?review_request_id=${data.review_request_id}&img_id=${data.img_id}`)
  },

  //publisher获得单张图片的单个人的详细人工审核结果
  getImageReviewDetail(data: any) {
    return http.get(`/get_image_review/?review_request_id=${data.review_request_id}&img_id=${data.img_id}&reviewer_id=${data.reviewer_id}`)
  },

  //publisher根据imgid获取detectionid
  getDetectionID(data: any) {
    return http.get(`/tasks_image/${data.img_id}/getdr/`)
  },

  deleteDetectionTask(data: any) {
    return http.delete(`/detection-task-delete/${data.task_id}/`)
  },

  clearDetectionHistory() {
    return http.delete('/detection-history/clear/')
  }

}
