<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNeedsStore } from '@/stores/needs'
import { ElMessage } from 'element-plus'
import { Search, TrendCharts, CircleCheck, Collection } from '@element-plus/icons-vue'
import ConciergeChat from '@/components/chat/ConciergeChat.vue'
import * as needsApi from '@/api/needs'

const route = useRoute()
const router = useRouter()
const store = useNeedsStore()
const needId = Number(route.params.id)
const streaming = ref(false)
const chatVisible = ref(false)
const selectedUserIds = ref<number[]>([])
const selecting = ref(false)
let eventSource: EventSource | null = null

const isSingleMode = computed(() => store.currentNeed?.selection_mode === 'single')

const stageDefs = [
  { key: 'tag_extraction', label: '标签提取', icon: Collection },
  { key: 'semantic_search', label: '语义检索', icon: Search },
  { key: 'rerank',          label: 'AI 精排', icon: TrendCharts },
  { key: 'done',            label: '匹配完成', icon: CircleCheck },
]

const currentStage = computed(() => {
  const last = store.matchProgress[store.matchProgress.length - 1]
  return last?.stage || 'tag_extraction'
})

const currentStageIdx = computed(() => stageDefs.findIndex(s => s.key === currentStage.value))

const stageMessages = computed(() => {
  const map: Record<string, string> = {}
  for (const p of store.matchProgress) map[p.stage] = p.message
  return map
})

function scoreColor(score: number) {
  if (score >= 85) return { color: 'var(--success)', bg: 'var(--success-light)' }
  if (score >= 70) return { color: 'var(--accent-hover)', bg: 'var(--accent-light)' }
  return { color: 'var(--text-secondary)', bg: 'var(--bg-surface)' }
}

function rankMedal(rank: number) {
  if (rank === 1) return '🥇'; if (rank === 2) return '🥈'; if (rank === 3) return '🥉'
  return `#${rank}`
}

onMounted(async () => {
  try { await store.fetchMatches(needId) } catch { startStream() }
})

function startStream() {
  streaming.value = true; store.matchProgress = []; store.matches = []
  eventSource = store.streamMatches(needId)
}

async function handleRefresh() {
  streaming.value = false; if (eventSource) eventSource.close()
  await store.refreshMatches(needId)
}

watch(() => store.currentNeed?.selected_user_ids, (ids) => {
  selectedUserIds.value = ids || []
}, { immediate: true })

async function handleSelect(userId: number) {
  selecting.value = true
  try {
    const { data } = await needsApi.selectUsers(needId, [userId])
    selectedUserIds.value = data.selected_user_ids || []
    store.currentNeed = data
    ElMessage.success(data.status === '已匹配' ? '已选定，需求自动关闭' : '已选择')
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e?.response?.data?.detail || e?.message || ''))
  } finally { selecting.value = false }
}

async function handleDeselect(userId: number) {
  selecting.value = true
  try {
    const { data } = await needsApi.deselectUser(needId, userId)
    selectedUserIds.value = data.selected_user_ids || []
    store.currentNeed = data
    ElMessage.success('已取消选择')
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e?.response?.data?.detail || e?.message || ''))
  } finally { selecting.value = false }
}

function handleContact(userId: number) {
  store.logBehavior('contact_click', { target_user_id: userId, need_id: needId })
  router.push(`/messages/${userId}?needId=${needId}`)
}

onUnmounted(() => { if (eventSource) eventSource.close() })
</script>

<template>
  <div class="match-page" v-loading="store.loading && !streaming">
    <div class="back-link" @click="router.push('/plaza')">&larr; 返回需求广场</div>

    <div class="match-layout">
      <!-- ════ Left Column: Results ════ -->
      <div class="match-left">
        <el-card v-if="store.currentNeed" shadow="never" class="page-card need-header">
          <h2 class="need-title">{{ store.currentNeed.title }}</h2>
          <p class="need-desc">{{ store.currentNeed.description }}</p>
          <div class="need-tags" v-if="store.currentNeed.req_tags?.length">
            <el-tag v-for="(t, idx) in store.currentNeed.req_tags" :key="idx" size="small" class="need-tag-item">{{ t }}</el-tag>
          </div>
        </el-card>

        <el-card v-if="streaming && store.matchProgress.length > 0" shadow="never" class="page-card progress-card">
          <div class="progress-steps">
            <div v-for="(s, idx) in stageDefs" :key="s.key" class="progress-step" :class="{ 'is-done': currentStageIdx > idx, 'is-active': currentStageIdx === idx }">
              <div class="step-dot">
                <el-icon v-if="currentStageIdx > idx" class="step-check"><CircleCheck /></el-icon>
                <el-icon v-else-if="currentStageIdx === idx" class="step-icon pulse"><component :is="s.icon" /></el-icon>
                <span v-else class="step-num">{{ idx + 1 }}</span>
              </div>
              <div class="step-body">
                <span class="step-label">{{ s.label }}</span>
                <span v-if="stageMessages[s.key]" class="step-msg">{{ stageMessages[s.key] }}</span>
              </div>
              <div v-if="idx < stageDefs.length - 1" class="step-connector" :class="{ filled: idx < currentStageIdx }" />
            </div>
          </div>
        </el-card>

        <div v-if="store.matches.length > 0" class="results-section">
          <div class="results-topbar">
            <h3 class="results-heading">匹配结果（{{ store.matches.length }} 人）</h3>
            <el-button :loading="store.loading" size="small" @click="handleRefresh">刷新匹配</el-button>
          </div>

          <el-card v-for="(m, idx) in store.matches" :key="m.user_id" shadow="never" class="page-card match-card">
            <div class="match-top">
              <div class="match-rank">
                <span class="rank-badge">{{ rankMedal(idx + 1) }}</span>
                <div class="match-user">
                  <span class="match-username">{{ m.username }}</span>
                  <span class="match-school">{{ m.school }}</span>
                </div>
              </div>
              <div class="match-score" :style="{ color: scoreColor(m.score).color }">
                <span class="score-num">{{ m.score }}</span><span class="score-unit">%</span>
              </div>
            </div>
            <el-progress :percentage="m.score" :color="scoreColor(m.score).color" :stroke-width="8" class="match-bar" />
            <blockquote class="match-reason">"{{ m.reason }}"</blockquote>
            <div class="match-tags" v-if="m.skill_tags?.length">
              <el-tag v-for="(t, tidx) in m.skill_tags.slice(0, 8)" :key="tidx" size="small" class="skill-tag">{{ t }}</el-tag>
            </div>
            <div class="match-actions">
              <el-button v-if="!selectedUserIds.includes(m.user_id)" :disabled="selecting || (isSingleMode && selectedUserIds.length >= 1)" type="primary" size="small" @click="handleSelect(m.user_id)">{{ isSingleMode ? '选TA' : '选择' }}</el-button>
              <el-button v-else type="success" size="small" @click="handleDeselect(m.user_id)" :disabled="selecting">已选择 ✓</el-button>
              <el-button size="small" @click="handleContact(m.user_id)">联系 TA</el-button>
            </div>
          </el-card>
        </div>

        <el-empty v-if="!store.loading && !streaming && store.matches.length === 0" description="暂无匹配结果，试试刷新" />
      </div>

      <!-- ════ Right Column: AI Advisor ════ -->
      <div class="match-right">
        <el-card shadow="never" class="page-card advisor-card">
          <template #header><span class="advisor-title">🤖 AI 匹配顾问</span></template>
          <p class="advisor-hint">对匹配结果不满意？告诉我你的偏好，我来帮你细化需求。</p>
          <el-button type="primary" size="small" style="width:100%" @click="chatVisible = true">开始对话</el-button>
        </el-card>
      </div>
    </div>

    <ConciergeChat
      v-if="store.currentNeed"
      :visible="chatVisible"
      @update:visible="chatVisible = $event"
      :need-id="needId"
      :need-title="store.currentNeed.title"
      :need-description="store.currentNeed.description"
      :need-tags="store.currentNeed.req_tags || []"
    />
  </div>
</template>

<style scoped>
.match-page { max-width: 1000px; margin: 0 auto; padding: 8px 0; }

.back-link { color: var(--primary); cursor: pointer; font-size: 14px; margin-bottom: 16px; display: inline-flex; align-items: center; gap: 4px; font-weight: 500; }
.back-link:hover { color: var(--primary-hover); }

/* -- Two-column layout -- */
.match-layout { display: grid; grid-template-columns: 1fr 260px; gap: 24px; align-items: start; }
.match-left { min-width: 0; }
.match-right { position: sticky; top: 80px; }

.page-card { border: 1px solid var(--card-border) !important; border-radius: var(--radius-lg) !important; box-shadow: var(--card-shadow) !important; margin-bottom: 16px; }

/* -- Need header -- */
.need-header { 
  background: linear-gradient(135deg, rgba(126, 172, 204, 0.08) 0%, rgba(126, 172, 204, 0.04) 50%, rgba(126, 172, 204, 0.06) 100%) !important;
  position: relative;
  overflow: hidden;
}
.need-header::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(126, 172, 204, 0.1) 0%, transparent 70%);
  animation: header-float 8s ease-in-out infinite;
}
@keyframes header-float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 20px); }
}
.need-title { font-size: 19px; font-weight: 700; margin: 0 0 8px 0; color: var(--text-primary); line-height: 1.3; }
.need-desc { font-size: 14px; color: var(--text-secondary); margin: 0 0 10px 0; line-height: 1.7; }
.need-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.need-tag-item { background: rgba(126, 172, 204, 0.1) !important; border-color: rgba(126, 172, 204, 0.2) !important; color: var(--primary) !important; }

/* -- Progress -- */
.progress-card { padding: 8px 0; }
.progress-steps { display: flex; align-items: flex-start; position: relative; }
.progress-step { flex: 1; display: flex; align-items: flex-start; position: relative; padding-right: 8px; min-width: 0; }
.progress-step::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 3px;
  height: 0;
  background: var(--primary);
  border-radius: 0 0 2px 2px;
  transition: height 0.5s ease;
}
.progress-step.is-active::after {
  height: 20px;
  animation: pulse-line 1.5s ease-in-out infinite;
}
@keyframes pulse-line {
  0%, 100% { opacity: 1; height: 20px; }
  50% { opacity: 0.5; height: 28px; }
}
.step-dot { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid var(--card-border); color: var(--text-muted); flex-shrink: 0; background: #fff; font-size: 14px; font-weight: 700; transition: all var(--transition-normal); }
.is-active .step-dot { border-color: var(--primary); color: var(--primary); box-shadow: var(--shadow-glow-blue); background: rgba(126, 172, 204, 0.08); }
.is-done .step-dot { background: var(--success-gradient); border-color: var(--success); color: #fff; box-shadow: 0 0 0 4px rgba(103, 194, 58, 0.15); }
.step-body { display: flex; flex-direction: column; margin-left: 12px; padding-top: 4px; min-width: 0; }
.step-label { font-size: 13px; font-weight: 600; white-space: nowrap; color: var(--text-primary); }
.step-msg { font-size: 11px; color: var(--text-secondary); margin-top: 3px; line-height: 1.4; }
.step-connector { position: absolute; top: 17px; left: 36px; right: calc(100% - 36px); height: 3px; background: var(--bg-surface); border-radius: 2px; transition: all var(--transition-normal); }
.step-connector.filled { background: linear-gradient(90deg, var(--primary), var(--success)); }
.pulse { animation: dot-pulse 1.2s ease-in-out infinite; }
@keyframes dot-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.6;transform:scale(0.95)} }

/* -- Results -- */
.results-topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.results-heading { font-size: 17px; font-weight: 700; color: var(--text-primary); margin: 0; }

/* Match card */
.match-card {
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--card-border) !important;
}
.match-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  opacity: 0;
  transform: scaleX(0);
  transition: all 0.3s ease;
}
.match-card:hover::before {
  opacity: 1;
  transform: scaleX(1);
}
.match-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--card-shadow-hover);
  border-color: rgba(126, 172, 204, 0.25) !important;
}

.match-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.match-rank { display: flex; align-items: center; gap: 12px; }
.rank-badge { font-size: 26px; min-width: 40px; text-align: center; transition: transform 0.3s ease; }
.match-card:hover .rank-badge { transform: scale(1.1); }
.match-user { display: flex; flex-direction: column; }
.match-username { font-size: 16px; font-weight: 700; color: var(--text-primary); transition: color 0.2s ease; }
.match-card:hover .match-username { color: var(--primary); }
.match-school { font-size: 13px; color: var(--text-secondary); margin-top: 3px; }
.match-score { 
  text-align: right; 
  flex-shrink: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.score-ring {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.score-ring::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(
    var(--success) 0deg,
    var(--accent) 60deg,
    var(--text-muted) 180deg,
    var(--text-muted) 360deg
  );
  mask: radial-gradient(farthest-side, transparent calc(100% - 8px), #fff calc(100% - 8px));
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 8px), #fff calc(100% - 8px));
}
.score-inner {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}
.score-num { font-size: 22px; font-weight: 800; line-height: 1; }
.score-unit { font-size: 11px; margin-left: 0; opacity: 0.7; }
.match-bar { margin-bottom: 12px; }
.match-bar :deep(.el-progress-bar) {
  border-radius: 4px;
  overflow: hidden;
}
.match-bar :deep(.el-progress-bar__outer) {
  background: var(--bg-surface);
  border-radius: 4px;
}
.match-reason { 
  border-left: 3px solid var(--accent); 
  padding: 12px 16px; 
  margin: 0 0 12px 0; 
  color: var(--text-secondary); 
  font-size: 14px; 
  line-height: 1.7; 
  background: linear-gradient(90deg, rgba(109, 179, 212, 0.06) 0%, rgba(109, 179, 212, 0.02) 100%);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  font-style: italic;
}
.match-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.skill-tag { 
  background: rgba(126, 172, 204, 0.08) !important; 
  border-color: rgba(126, 172, 204, 0.15) !important; 
  color: var(--primary) !important;
  transition: all 0.2s ease;
}
.skill-tag:hover {
  background: rgba(126, 172, 204, 0.15) !important;
  transform: translateY(-1px);
}
.match-actions { display: flex; gap: 8px; }
.match-actions :deep(.el-button) {
  transition: all 0.2s ease;
}
.match-actions :deep(.el-button:hover) {
  transform: translateY(-1px);
}

/* -- Right advisor -- */
.advisor-card { 
  text-align: center; 
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}
.advisor-card::before {
  content: '';
  position: absolute;
  top: -60%;
  right: -30%;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(109, 179, 212, 0.12) 0%, transparent 70%);
}
.advisor-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow-hover);
}
.advisor-title { 
  font-size: 16px; 
  font-weight: 700; 
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.advisor-title::before {
  content: '🤖';
  animation: robot-bounce 2s ease-in-out infinite;
}
@keyframes robot-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}
.advisor-hint { font-size: 13px; color: var(--text-secondary); line-height: 1.7; margin: 8px 0 16px; }
.advisor-card :deep(.el-button--primary) {
  background: var(--primary-gradient) !important;
  border: none !important;
  box-shadow: 0 4px 14px rgba(126, 172, 204, 0.3) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.advisor-card :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(126, 172, 204, 0.4) !important;
}
.advisor-card :deep(.el-button--primary:active) {
  transform: translateY(0);
}

/* Global button enhancements */
:deep(.el-button--primary) {
  background: var(--primary-gradient) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(126, 172, 204, 0.25) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
:deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(126, 172, 204, 0.35) !important;
}
:deep(.el-button--primary:active) {
  transform: translateY(0);
}
:deep(.el-button--success) {
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.25) !important;
}
:deep(.el-button--success:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(103, 194, 58, 0.35) !important;
}

@media (max-width: 768px) {
  .match-layout { grid-template-columns: 1fr; }
  .match-right { position: static; }
}
</style>
