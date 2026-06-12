import { api, BASE_UPLOAD_URL } from './api'

export interface TemplateDto {
  id: string
  name: string
  template_type: 'contract' | 'act' | 'appendix' | 'invoice' | 'other'
  description?: string | null
  content: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface GenerateResult {
  message: string
  document_id: string | null
  file_path: string
  rendered_text: string
  download_url: string
}

export const templateService = {
  async getTemplates(template_type?: string): Promise<TemplateDto[]> {
    const { data } = await api.get('/templates', { params: template_type ? { template_type } : undefined })
    return data
  },

  async createTemplate(payload: Partial<TemplateDto>): Promise<TemplateDto> {
    const { data } = await api.post('/templates', payload)
    return data
  },

  async updateTemplate(id: string, payload: Partial<TemplateDto>): Promise<TemplateDto> {
    const { data } = await api.put(`/templates/${id}`, payload)
    return data
  },

  async deleteTemplate(id: string) {
    const { data } = await api.delete(`/templates/${id}`)
    return data
  },

  async generate(id: string, payload: {
    project_id: string
    contract_id?: string
    employee_id?: string
    extra_fields?: Record<string, string>
    save_as_document?: boolean
  }): Promise<GenerateResult> {
    const { data } = await api.post(`/templates/${id}/generate`, payload)
    return data
  },

  getGeneratedDownloadUrl(downloadUrl: string) {
    return `${BASE_UPLOAD_URL}${downloadUrl}`
  },
}
