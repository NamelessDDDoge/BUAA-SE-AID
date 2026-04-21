import http from './request'
import { ref } from 'vue'


export default {
  // 获取文件列表
  getFiles(params: {
    page: number;
    page_size: number;
    query?: string;
    categories?: string;
    startTime?: string;
    endTime?: string;
  }) {
    return http.get('/get_files/', { params });
  },

  // 删除文件
  deleteFile(fileId: number) {
    return http.delete(`/upload/${fileId}/delete/`);
  },

  // 获取文件图片列表
  getFileImages(fileId: number, params: {
    page: number;
    page_size: number;
    isDetect: string;
    isReview: string;
    isFake: string;
  }) {
    return http.get(`/upload/get_all_file_images/${fileId}/`, { params });
  },

  // 删除单张图片
  deleteImage(imageId: number) {
    return http.delete(`/delete_image_upload/${imageId}/`);
  }
}
