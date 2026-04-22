export type DetectionType = 'image' | 'paper' | 'review'

export type MethodSwitches = {
  llm: boolean
  ela: boolean
  exif: boolean
  cmd: boolean
  urn_coarse_v2: boolean
  urn_blurring: boolean
  urn_brute_force: boolean
  urn_contrast: boolean
  urn_inpainting: boolean
}

export interface UploadedResourceFile {
  file_id: number
  name: string
  resource_type: string
}

export interface TaskOption {
  title: string
  value: string
}

export const createDefaultMethodSwitches = (): MethodSwitches => ({
  llm: true,
  ela: true,
  exif: true,
  cmd: true,
  urn_coarse_v2: true,
  urn_blurring: true,
  urn_brute_force: true,
  urn_contrast: true,
  urn_inpainting: true,
})
