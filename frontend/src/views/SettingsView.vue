<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as settingsApi from '@/api/settings'

const apiKey = ref('')
const loading = ref(false)
const saving = ref(false)
const hasKey = ref(false)
const maskedKey = ref('')

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await settingsApi.getSettings()
    hasKey.value = data.has_api_key
    maskedKey.value = data.api_key_masked
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function save() {
  const key = apiKey.value.trim()
  if (!key) { ElMessage.warning('请输入 API Key'); return }
  if (!key.startsWith('sk-')) { ElMessage.warning('API Key 应以 sk- 开头'); return }

  saving.value = true
  try {
    await settingsApi.updateSettings({ deepseek_api_key: key })
    ElMessage.success('API Key 已保存，重启服务后生效')
    apiKey.value = ''
    load()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e?.response?.data?.detail || e?.message || ''))
  } finally { saving.value = false }
}
</script>

<template>
  <div class="settings-page">
    <h2>系统设置</h2>

    <el-card v-loading="loading" shadow="never" class="section-card">
      <template #header><span class="card-title">DeepSeek API 配置</span></template>

      <div class="setting-row">
        <span class="setting-label">API Key 状态</span>
        <el-tag :type="hasKey ? 'success' : 'danger'">
          {{ hasKey ? '已配置 ' + maskedKey : '未配置' }}
        </el-tag>
      </div>

      <div class="setting-row hint">
        获取 API Key: 前往 <a href="https://platform.deepseek.com/api_keys" target="_blank">DeepSeek 开放平台</a> 创建
      </div>

      <div class="setting-row">
        <el-input
          v-model="apiKey"
          placeholder="sk-..."
          type="password"
          show-password
          class="key-input"
        />
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>

      <el-alert type="warning" :closable="false" show-icon style="margin-top:12px">
        修改 API Key 后需要重启后端服务才能生效。
      </el-alert>
    </el-card>

    <el-card shadow="never" class="section-card" style="margin-top:16px">
      <template #header><span class="card-title">本地模型</span></template>
      <p class="hint">Qwen3-Embedding-0.6B 和 Qwen3-Reranker-0.6B 需要从 HuggingFace 下载到 <code>backend/model_cache/</code> 目录。首次启动会自动下载。</p>
    </el-card>
  </div>
</template>

<style scoped>
.settings-page { max-width: 600px; margin: 0 auto; padding: 24px 16px; }
.settings-page h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; }
.section-card { border: 1px solid #e8e8e8; border-radius: 8px; }
.card-title { font-size: 15px; font-weight: 600; }
.setting-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.setting-label { font-size: 14px; color: #1f2328; min-width: 100px; }
.key-input { flex: 1; }
.hint { font-size: 13px; color: #656d76; }
.hint a { color: #0969da; }
</style>
