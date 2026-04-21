import http from './request'

export default {
  getLogs(params: any) {
    return http.get('/user_action_log/', { params });
  },

  deleteLog(logId: number) {
    return http.delete(`/user_action_log/${logId}/`);
  },

  downloadLogs(params: {
    query?: number[];
    status?: string;
    operation_type?: string;
    startTime?: string;
    endTime?: string;
  }) {
    return http.get('/user_action_log/download/', { 
      params: {
        ...params,
        query: params.query?.join(',')
      },
      responseType: 'blob'
    });
  }
} 