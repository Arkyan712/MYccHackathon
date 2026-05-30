<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Need } from '@/types'
import * as needsApi from '@/api/needs'

const router = useRouter()
const needs = ref<Need[]>([])
const loading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await needsApi.getMyNeeds()
    needs.value = data
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function handleClose(need: Need) {
  try {
    await ElMessageBox.confirm('确定关闭这个需求吗？', '确认', { type: 'warning' })
  } catch { return }
  try {
    await needsApi.closeNeed(need.id)
    ElMessage.success('已关闭')
    load()
  } catch { ElMessage.error('操作失败') }
}

async function handleDelete(need: Need) {
  try {
    await ElMessageBox.confirm('确定删除这个需求吗？此操作不可恢复', '确认删除', { type: 'error' })
  } catch { return }
  try {
    await needsApi.deleteNeed(need.id)
    ElMessage.success('已删除')
    load()
  } catch { ElMessage.error('删除失败') }
}

async function handleReopen(need: Need) {
  try {
    await needsApi.updateNeed(need.id, { status: '开放' })
    ElMessage.success('已重新开放')
    load()
  } catch { ElMessage.error('操作失败') }
}

function statusTag(status: string) {
  switch (status) {
    case '开放': return 'success'
    case '已匹配': return 'warning'
    case '关闭': return 'info'
    default: return ''
  }
}

function goMatch(needId: number) { router.push(`/needs/${needId}/matches`) }
</script>

<template>
  <div class="manage-page">
    <div class="page-header">
      <h2>我的需求</h2>
      <span class="page-count">共 {{ needs.length }} 个</span>
    </div>

    <el-card v-loading="loading" shadow="never" class="page-card">
      <el-empty v-if="!loading && needs.length === 0" description="还没有发布过需求" />

      <div v-else class="need-list">
        <div v-for="n in needs" :key="n.id" class="need-row">
          <div class="need-info" @click="goMatch(n.id)">
            <div class="need-top">
              <el-tag :type="n.type === '求助' ? 'danger' : n.type === '组队' ? 'success' : 'warning'" size="small">
                {{ n.type }}
              </el-tag>
              <el-tag :type="statusTag(n.status)" size="small" effect="plain">{{ n.status }}</el-tag>
              <el-tag v-if="n.selection_mode === 'multi'" size="small" effect="plain" type="info">多选</el-tag>
              <span v-if="n.selected_user_ids?.length" class="selected-badge">
                已选 {{ n.selected_user_ids.length }} 人
              </span>
            </div>
            <h3 class="need-title">{{ n.title }}</h3>
            <p class="need-desc">{{ n.description.slice(0, 80) }}{{ n.description.length > 80 ? '...' : '' }}</p>
            <span class="need-date">{{ n.created_at.slice(0, 10) }}</span>
          </div>
          <div class="need-actions">
            <el-button v-if="n.status === '开放'" size="small" @click="goMatch(n.id)">查看匹配</el-button>
            <el-button v-if="n.status === '开放'" size="small" @click="handleClose(n)">关闭</el-button>
            <el-button v-if="n.status === '已匹配'" size="small" @click="goMatch(n.id)">查看结果</el-button>
            <el-button v-if="n.status === '关闭'" size="small" type="warning" @click="handleReopen(n)">重新开放</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(n)">删除</el-button>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.manage-page { max-width: 800px; margin: 0 auto; padding: 24px 16px; }
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
.page-header h2 { font-size: 20px; font-weight: 600; margin: 0; }
.page-count { font-size: 14px; color: #656d76; }
.page-card { border: 1px solid #e8e8e8 !important; border-radius: 8px !important; }

.need-list { display: flex; flex-direction: column; }
.need-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 0; border-bottom: 1px solid #f0f0f0; gap: 16px;
}
.need-row:last-child { border-bottom: none; }
.need-info { flex: 1; min-width: 0; cursor: pointer; }
.need-info:hover .need-title { color: #0969da; }
.need-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.need-title { font-size: 15px; font-weight: 600; margin: 0 0 4px; color: #1a1a2e; }
.need-desc { font-size: 13px; color: #656d76; margin: 0 0 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.need-date { font-size: 12px; color: #bbb; }
.need-actions { display: flex; gap: 6px; flex-shrink: 0; }
.selected-badge { font-size: 12px; color: #0969da; font-weight: 500; }
</style>
