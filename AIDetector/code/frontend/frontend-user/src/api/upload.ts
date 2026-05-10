import http from './request'

export default {
  uploadFile(data: any, onUploadProgress?: (progressEvent: any) => void) {
    return http.post('/upload/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress,
    })
  },

  listZipDocumentEntries(data: any) {
    return http.post('/upload/zip_entries/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000,
    })
  },

  uploadZipDocumentEntry(data: any, onUploadProgress?: (progressEvent: any) => void) {
    return http.post('/upload/zip_entry/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress,
      timeout: 60000,
    })
  },

  getExtractedImages(data: any) {
    return http.get(`/upload/${data.file_id}/extract_images/?page=${data.page_number}&page_size=${data.page_size}`)
  },

  getResourceTextPreview(fileId: number, taskId?: string | number | null) {
    return http.get(`/upload/${fileId}/preview_text/`, {
      params: taskId ? { task_id: taskId } : undefined,
    })
  },

  addTag(data: any) {
    console.log(data)
    return http.post(`/upload/${data.fileId}/addTag/`, {tag:data.tag})
  }
}
