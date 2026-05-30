import api from './client'

export function getSettings() {
  return api.get<{ has_api_key: boolean; api_key_masked: string; base_url: string; pro_model: string; flash_model: string }>('/settings')
}

export function updateSettings(data: { deepseek_api_key: string }) {
  return api.put<{ ok: boolean; message: string }>('/settings', data)
}
