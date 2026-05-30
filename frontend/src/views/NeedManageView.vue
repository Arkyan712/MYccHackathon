<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Need } from '@/types'
import * as needsApi from '@/api/needs'

const router = useRouter()
const needs = ref<Need[]>([])
const loading = ref(false)

const stats = computed(() => ({
  open: needs.value.filter(n => n.status === '开放').length,
  matched: needs.value.filter(n => n.status === '已匹配').length,
  closed: needs.value.filter(n => n.status === '关闭').length,
}))

const statCards = computed(() => [
  { label: '开放中', count: stats.value.open, color: 'var(--primary)', bg: 'var(--primary-light)', icon: '●' },
  { label: '已匹配', count: stats.value.matched, color: 'var(--success)', bg: 'var(--success-light)', icon: '✓' },
  { label: '已关闭', count: stats.value.closed, color: 'var(--text-muted)', bg: 'var(--bg-surface)', icon: '○' },
])

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
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>我的需求</h2>
        <p>管理你发布的所有需求，查看匹配状态</p>
      </div>
      <el-button type="primary" @click="router.push('/needs/new')">发布需求</el-button>
    </div>

    <!-- Stats cards -->
    <div class="stats-row">
      <div v-for="s in statCards" :key="s.label" class="stat-card" :style="{ '--stat-color': s.color, '--stat-bg': s.bg }">
        <span class="stat-icon">{{ s.icon }}</span>
        <div class="stat-body">
          <span class="stat-count">{{ s.count }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- Need list -->
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
.manage-page { max-width: 1000px; margin: 0 auto; padding: 8px 0; }

/* -- Page header -- */
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; gap: 16px; }
.page-header h2 { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; }
.page-header p { font-size: 14px; color: var(--text-secondary); margin: 0; }

/* -- Stats row -- */
.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
  background: var(--card-bg); border: 1px solid var(--card-border);
  border-radius: var(--radius-lg); padding: 20px 24px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: var(--card-shadow); transition: all var(--transition-normal);
}
.stat-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-2px); }
.stat-icon { font-size: 18px; color: var(--stat-color); width: 44px; height: 44px; border-radius: var(--radius-md); background: var(--stat-bg); display: flex; align-items: center; justify-content: center; }
.stat-body { display: flex; flex-direction: column; }
.stat-count { font-size: 28px; font-weight: 800; color: var(--text-primary); line-height: 1.1; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

/* -- Card & List -- */
.page-card { border: 1px solid var(--card-border) !important; border-radius: var(--radius-lg) !important; box-shadow: var(--card-shadow) !important; }
.need-list { display: flex; flex-direction: column; }
.need-row { display: flex; align-items: center; justify-content: space-between; padding: 18px 0; border-bottom: 1px solid #f0f0f0; gap: 20px; }
.need-row:last-child { border-bottom: none; }
.need-info { flex: 1; min-width: 0; cursor: pointer; }
.need-info:hover .need-title { color: var(--primary); }
.need-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.need-title { font-size: 15px; font-weight: 600; margin: 0 0 4px; color: var(--text-primary); transition: color var(--transition-fast); }
.need-desc { font-size: 13px; color: var(--text-secondary); margin: 0 0 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.need-date { font-size: 12px; color: var(--text-muted); }
.need-actions { display: flex; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
.selected-badge { font-size: 12px; color: var(--success); font-weight: 600; }

@media (max-width: 640px) {
  .stats-row { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; }
  .need-row { flex-direction: column; align-items: stretch; }
  .need-actions { justify-content: flex-end; }
}
</style>
