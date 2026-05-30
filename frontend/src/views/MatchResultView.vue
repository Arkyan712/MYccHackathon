<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
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

const currentStageIdx = computed(() =>
  stageDefs.findIndex(s => s.key === currentStage.value)
)

const stageMessages = computed(() => {
  const map: Record<string, string> = {}
  for (const p of store.matchProgress) {
    map[p.stage] = p.message
  }
  return map
})

function scoreColor(score: number) {
  if (score >= 85) return { color: '#1a7f37', bg: '#dafbe1' }
  if (score >= 70) return { color: '#bf8700', bg: '#fff8c5' }
  return { color: '#656d76', bg: '#f0f0f0' }
}

function rankMedal(rank: number) {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return `#${rank}`
}

onMounted(async () => {
  try {
    await store.fetchMatches(needId)
  } catch {
    startStream()
  }
})

function startStream() {
  streaming.value = true
  store.matchProgress = []
  store.matches = []
  eventSource = store.streamMatches(needId)
}

async function handleRefresh() {
  streaming.value = false
  if (eventSource) eventSource.close()
  await store.refreshMatches(needId)
}

function handleRefine() {
  chatVisible.value = true
}

function handleContact(userId: number) {
  store.logBehavior('contact_click', { target_user_id: userId, need_id: needId })
  router.push(`/messages/${userId}?needId=${needId}`)
}

// Sync selected IDs from currentNeed
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

onUnmounted(() => {
  if (eventSource) eventSource.close()
})
</script>

<template>
  <div class="match-page" v-loading="store.loading && !streaming">
    <!-- Back link -->
    <div class="back-link" @click="router.push('/')">
      &larr; 返回需求广场
    </div>

    <!-- Page header: need summary -->
    <el-card v-if="store.currentNeed" shadow="never" class="page-card need-header">
      <h2 class="need-title">{{ store.currentNeed.title }}</h2>
      <p class="need-desc">{{ store.currentNeed.description }}</p>
      <div class="need-tags" v-if="store.currentNeed.req_tags?.length">
        <el-tag
          v-for="(t, i) in store.currentNeed.req_tags"
          :key="i"
          size="small"
          class="need-tag-item"
        >{{ t }}</el-tag>
      </div>
    </el-card>

    <!-- Match progress indicator -->
    <el-card
      v-if="streaming && store.matchProgress.length > 0"
      shadow="never"
      class="page-card progress-card"
    >
      <div class="progress-steps">
        <div
          v-for="(s, idx) in stageDefs"
          :key="s.key"
          class="progress-step"
          :class="{
            'is-done': currentStageIdx > idx,
            'is-active': currentStageIdx === idx,
          }"
        >
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

    <!-- Match results -->
    <div v-if="store.matches.length > 0" class="results-section">
      <h3 class="results-heading">匹配结果（{{ store.matches.length }} 人）</h3>

      <el-card shadow="never" class="page-card comparison-table">
        <div class="comparison-title">候选人对比表</div>
        <el-table :data="store.matches" size="small">
          <el-table-column label="候选人" min-width="110">
            <template #default="{ row }">
              <strong>{{ row.username }}</strong>
              <div class="table-sub">{{ row.school || '未填写学校' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="匹配度" width="90">
            <template #default="{ row }">
              <span :style="{ color: scoreColor(row.score).color, fontWeight: 600 }">{{ row.score }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="技能标签" min-width="180">
            <template #default="{ row }">
              <div class="table-tags">
                <el-tag v-for="tag in row.skill_tags.slice(0, 4)" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="推荐理由" min-width="240">
            <template #default="{ row }">
              <span class="table-reason">{{ row.reason }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card
        v-for="(m, i) in store.matches"
        :key="m.user_id"
        shadow="never"
        class="page-card match-card"
      >
        <div class="match-top">
          <div class="match-rank">
            <span class="rank-badge">{{ rankMedal(i + 1) }}</span>
            <div class="match-user">
              <span class="match-username">{{ m.username }}</span>
              <span class="match-school">{{ m.school }}</span>
            </div>
          </div>
          <div class="match-score" :style="{ color: scoreColor(m.score).color }">
            <span class="score-num">{{ m.score }}</span>
            <span class="score-unit">%</span>
          </div>
        </div>

        <el-progress
          :percentage="m.score"
          :color="scoreColor(m.score).color"
          :stroke-width="8"
          class="match-bar"
        />

        <blockquote class="match-reason">
          "{{ m.reason }}"
        </blockquote>

        <div class="match-tags" v-if="m.skill_tags?.length">
          <el-tag
            v-for="(t, idx) in m.skill_tags.slice(0, 8)"
            :key="idx"
            size="small"
            class="skill-tag"
          >{{ t }}</el-tag>
        </div>

        <div class="match-actions">
          <el-button
            v-if="!selectedUserIds.includes(m.user_id)"
            :disabled="selecting || (isSingleMode && selectedUserIds.length >= 1)"
            type="primary"
            size="default"
            @click="handleSelect(m.user_id)"
          >
            {{ isSingleMode ? '选TA' : '选择' }}
          </el-button>
          <el-button
            v-else
            type="success"
            size="default"
            @click="handleDeselect(m.user_id)"
            :disabled="selecting"
          >
            已选择 ✓
          </el-button>
          <el-button size="default" @click="handleContact(m.user_id)">
            联系 TA
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- Empty state -->
    <el-empty
      v-if="!store.loading && !streaming && store.matches.length === 0"
      description="暂无匹配结果，试试刷新"
    />

    <!-- Action bar -->
    <div class="action-bar">
      <el-button :loading="store.loading" @click="handleRefresh" size="default">
        刷新匹配
      </el-button>
      <el-button type="primary" @click="handleRefine" size="default">
        AI 追问细化
      </el-button>
    </div>

    <!-- Concierge Chat Dialog -->
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
/* ── Layout ── */
.match-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* ── Back link ── */
.back-link {
  color: #0969da;
  cursor: pointer;
  font-size: 14px;
  margin-bottom: 16px;
  display: inline-block;
}
.back-link:hover {
  text-decoration: underline;
}

/* ── Cards (global) ── */
.page-card {
  border: 1px solid #e8e8e8 !important;
  border-radius: 8px !important;
  margin-bottom: 16px;
}

/* ── Need header ── */
.need-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #1a1a2e;
}
.need-desc {
  font-size: 14px;
  color: #656d76;
  margin: 0 0 12px 0;
  line-height: 1.6;
}
.need-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.need-tag-item {
  margin: 0;
}

/* ── Progress steps ── */
.progress-card {
  padding: 4px 0;
}
.progress-steps {
  display: flex;
  align-items: flex-start;
}
.progress-step {
  flex: 1;
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-right: 4px;
  min-width: 0;
}
.step-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #d0d7de;
  color: #8b949e;
  flex-shrink: 0;
  background: #fff;
  font-size: 13px;
}
.step-dot .step-num {
  font-weight: 600;
}
.is-active .step-dot {
  border-color: #0969da;
  color: #0969da;
}
.is-done .step-dot {
  background: #1a7f37;
  border-color: #1a7f37;
  color: #fff;
}
.step-body {
  display: flex;
  flex-direction: column;
  margin-left: 10px;
  padding-top: 4px;
  min-width: 0;
}
.step-label {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}
.step-msg {
  font-size: 12px;
  color: #656d76;
  margin-top: 2px;
}
.step-connector {
  position: absolute;
  top: 15px;
  left: 32px;
  right: calc(100% - 32px);
  height: 2px;
  background: #e8e8e8;
}
.step-connector.filled {
  background: #1a7f37;
}
.is-active .step-connector {
  right: calc(100% + 16px);
}

/* Pulsing animation for active step */
.pulse {
  animation: dot-pulse 1.2s ease-in-out infinite;
}
@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

/* ── Results heading ── */
.results-heading {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #1a1a2e;
}

.comparison-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}
.table-sub {
  margin-top: 2px;
  color: #656d76;
  font-size: 12px;
}
.table-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.table-reason {
  display: -webkit-box;
  overflow: hidden;
  color: #656d76;
  font-size: 12px;
  line-height: 1.5;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ── Match card ── */
.match-card {
  transition: box-shadow 0.15s;
}
.match-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.match-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.match-rank {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rank-badge {
  font-size: 20px;
  min-width: 34px;
  text-align: center;
}
.match-user {
  display: flex;
  flex-direction: column;
}
.match-username {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}
.match-school {
  font-size: 12px;
  color: #656d76;
  margin-top: 2px;
}
.match-score {
  text-align: right;
  flex-shrink: 0;
}
.score-num {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}
.score-unit {
  font-size: 14px;
  margin-left: 1px;
}

.match-bar {
  margin-bottom: 12px;
}

.match-reason {
  border-left: 3px solid #d0d7de;
  padding: 8px 14px;
  margin: 0 0 12px 0;
  color: #656d76;
  font-size: 13px;
  font-style: italic;
  line-height: 1.6;
  background: #f6f8fa;
  border-radius: 0 4px 4px 0;
}

.match-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.skill-tag {
  margin: 0;
}

.match-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

/* ── Action bar ── */
.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.action-bar .el-button--primary {
  background-color: #0969da;
  border-color: #0969da;
}

/* ── Refine alert ── */
.refine-alert {
  margin-top: 16px;
  border-radius: 8px;
}
</style>
