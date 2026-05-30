<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { AgentMessage, NeedDraft } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useAgentStore()

const inputText = ref('')
const showSessions = ref(true)
const showTasks = ref(true)
const isMobile = ref(window.innerWidth < 768)

const activeSessionId = ref<number | null>(null)
const fileInput = ref<HTMLInputElement>()

onMounted(async () => {
  await store.fetchSessions()
  const sid = route.params.sessionId
  if (sid) {
    activeSessionId.value = Number(sid)
    await store.loadSession(Number(sid))
  } else if (store.sessions.length > 0) {
    // Navigate to most recent session instead of creating a new one
    const latest = store.sessions[0]
    router.replace(`/agent/${latest.id}`)
  }
  // If no sessions at all, stay on /agent with empty state (user clicks "新对话" to create)
  window.addEventListener('resize', () => { isMobile.value = window.innerWidth < 768 })
})

watch(() => route.params.sessionId, async (sid) => {
  if (sid) {
    activeSessionId.value = Number(sid)
    await store.loadSession(Number(sid))
  }
})

async function handleNewSession() {
  const id = await store.createSession()
  activeSessionId.value = id
  router.push(`/agent/${id}`)
}

async function handleSelectSession(id: number) {
  activeSessionId.value = id
  router.push(`/agent/${id}`)
}

async function handleDeleteSession(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个会话吗？', '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await store.deleteSession(id)
    if (activeSessionId.value === id) {
      activeSessionId.value = null
      router.push('/agent')
    }
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error('删除失败: ' + (e?.response?.data?.detail || e?.message || ''))
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || !activeSessionId.value) return
  inputText.value = ''

  if (text.startsWith('/plan ')) {
    await store.triggerPlan(activeSessionId.value, text.slice(6))
  } else {
    await store.sendMessage(activeSessionId.value, text)
  }
  scrollToBottom()
}

const uploading = ref(false)

async function handleFileUpload(file: File) {
  if (!activeSessionId.value) {
    ElMessage.warning('请先创建一个会话')
    return
  }
  uploading.value = true
  ElMessage.info(`正在上传并分析 ${file.name}...`)
  try {
    const result = await store.uploadFile(activeSessionId.value, file)
    if (result) {
      ElMessage.success(`${file.name} 分析完成！`)
    }
  } catch (e: any) {
    ElMessage.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally {
    uploading.value = false
    scrollToBottom()
  }
}

async function handlePublishDrafts(drafts: NeedDraft[]) {
  if (!activeSessionId.value) return
  await store.confirmPublish(activeSessionId.value, drafts)
  ElMessage.success('需求已发布，匹配中...')
}

function getMessageDrafts(message: AgentMessage): NeedDraft[] {
  const drafts = message.extra_metadata?.drafts
  return Array.isArray(drafts) ? drafts as NeedDraft[] : []
}

function scrollToBottom() {
  nextTick(() => {
    const el = document.querySelector('.chat-messages')
    if (el) el.scrollTop = el.scrollHeight
  })
}
</script>

<template>
  <div class="agent-view">
    <!-- Left: Sessions -->
    <div class="agent-left" :class="{ 'is-hidden': !showSessions && isMobile }">
      <div class="sessions-panel">
        <div class="sessions-hd">
          <span class="sessions-title">会话</span>
          <el-button :icon="Plus" size="small" circle @click="handleNewSession" />
        </div>
        <div class="sessions-list">
          <div
            v-for="s in store.sessions"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === activeSessionId }"
            @click="handleSelectSession(s.id)"
          >
            <div class="session-info">
              <div class="session-title">{{ s.title }}</div>
              <div class="session-date">{{ s.updated_at?.slice(0, 16) }}</div>
            </div>
            <el-button
              size="small"
              text
              type="danger"
              @click.stop="handleDeleteSession(s.id)"
            >×</el-button>
          </div>
          <el-empty v-if="store.sessions.length === 0" description="暂无会话" :image-size="40" />
        </div>
      </div>
    </div>

    <!-- Center: Chat -->
    <div class="agent-center">
      <div class="chat-panel">
        <!-- Top bar -->
        <div class="chat-topbar">
          <el-button v-if="isMobile" text @click="showSessions = !showSessions">
            会话
          </el-button>
          <span class="chat-title">{{ store.currentSession?.title || '智能助手' }}</span>
          <el-button v-if="isMobile" text @click="showTasks = !showTasks">
            任务
          </el-button>
        </div>

        <!-- Messages -->
        <div class="chat-messages" v-loading="store.loading">
          <el-empty v-if="store.messages.length === 0 && !store.loading" description="我是你的AI助手，可以帮你分析文件、发布需求、查看匹配结果。上传一个通知文件试试吧！" :image-size="64" />

          <div v-for="m in store.messages" :key="m.id" class="chat-msg" :class="m.role">
            <div class="msg-avatar">
              {{ m.role === 'user' ? '我' : m.role === 'assistant' ? 'AI' : '!' }}
            </div>
            <div class="msg-bubble" :class="m.role">
              <div class="msg-content">{{ m.content }}</div>

              <!-- Draft preview -->
              <div v-if="getMessageDrafts(m).length" class="draft-preview">
                <div v-for="(d, i) in getMessageDrafts(m)" :key="i" class="draft-card">
                  <div class="draft-top">
                    <el-tag size="small" effect="plain">{{ d.type }}</el-tag>
                    <span class="draft-mode">单选/多选</span>
                  </div>
                  <strong>{{ d.title }}</strong>
                  <p>{{ d.description?.slice(0, 100) }}{{ d.description?.length > 100 ? '...' : '' }}</p>
                </div>
                <el-button type="primary" size="small" @click="handlePublishDrafts(getMessageDrafts(m))">
                  确认发布
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="chat-input-bar">
          <input
            ref="fileInput"
            type="file"
            accept=".txt,.docx,.pdf"
            style="display:none"
            @change="(e) => { const el = e.target as HTMLInputElement; const f = el.files?.[0]; if (f) { handleFileUpload(f).finally(() => { el.value = '' }) } }"
          />
          <el-button text class="upload-btn" :loading="uploading" @click="fileInput?.click()">
            {{ uploading ? '⏳' : '📎' }}
          </el-button>
          <el-input
            v-model="inputText"
            placeholder="输入消息，或输入 /plan 目标 来制定计划..."
            :disabled="store.isStreaming"
            @keyup.enter="handleSend"
            class="chat-input"
          />
          <el-button type="primary" :disabled="!inputText.trim() || store.isStreaming" @click="handleSend">
            发送
          </el-button>
        </div>
      </div>
    </div>

    <!-- Right: Tasks -->
    <div class="agent-right" :class="{ 'is-hidden': !showTasks && isMobile }">
      <div class="tasks-panel">
        <div class="suggestions-block">
          <div class="tasks-hd">主动建议</div>
          <div v-if="store.suggestions.length === 0" class="tasks-empty">暂无建议</div>
          <div
            v-for="s in store.suggestions"
            :key="s"
            class="suggestion-item"
            @click="inputText = s"
          >
            {{ s }}
          </div>
        </div>
        <div class="tasks-hd">任务进度</div>
        <div v-if="store.tasks.length === 0" class="tasks-empty">暂无任务</div>
        <div v-for="t in store.tasks" :key="t.id" class="task-item">
          <div class="task-status" :class="t.status">
            {{ t.status === 'done' ? '✓' : t.status === 'running' ? '●' : t.status === 'failed' ? '✗' : '○' }}
          </div>
          <div class="task-info">
            <div class="task-goal">{{ t.goal }}</div>
            <div v-if="t.assigned_agent" class="task-agent">{{ t.assigned_agent }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-view {
  display: flex;
  height: calc(100vh - 64px);
  overflow: hidden;
}

/* -- Left: Sessions -- */
.agent-left {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid #e8e8e8;
  background: #fafbfc;
}
.sessions-panel { display: flex; flex-direction: column; height: 100%; }
.sessions-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid #e8e8e8;
}
.sessions-title { font-size: 15px; font-weight: 600; }
.sessions-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: 6px; cursor: pointer;
  margin-bottom: 2px; transition: background 0.15s;
}
.session-item:hover { background: #eef5ff; }
.session-item.active { background: #dbeafe; }
.session-title { font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-date { font-size: 11px; color: #8b949e; margin-top: 2px; }

/* -- Center: Chat -- */
.agent-center { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-panel { display: flex; flex-direction: column; height: 100%; }
.chat-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid #e8e8e8; background: #fff;
}
.chat-title { font-size: 15px; font-weight: 600; }

.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 14px;
  background: #fafbfc;
}

.chat-msg { display: flex; gap: 10px; max-width: 85%; }
.chat-msg.user { align-self: flex-end; flex-direction: row-reverse; }
.chat-msg.assistant, .chat-msg.system { align-self: flex-start; }

.msg-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex-shrink: 0;
}
.chat-msg.user .msg-avatar { background: #0969da; color: #fff; }
.chat-msg.assistant .msg-avatar { background: #e8f4fd; color: #0969da; }
.chat-msg.system .msg-avatar { background: #fff3cd; color: #856404; }

.msg-bubble {
  padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6;
}
.chat-msg.user .msg-bubble { background: #0969da; color: #fff; }
.chat-msg.assistant .msg-bubble { background: #fff; border: 1px solid #e8e8e8; }
.chat-msg.system .msg-bubble { background: #fffbe6; border: 1px solid #ffe58f; font-size: 13px; }

.msg-content {
  word-break: break-word;
  white-space: pre-wrap;
}

.draft-preview { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; }
.draft-card {
  background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
  padding: 10px 12px;
}
.draft-card p { font-size: 12px; color: #656d76; margin: 4px 0; }
.draft-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.draft-mode { font-size: 11px; color: #8b949e; }

/* -- Input -- */
.chat-input-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px; border-top: 1px solid #e8e8e8; background: #fff;
}
.chat-input { flex: 1; }

/* -- Right: Tasks -- */
.agent-right {
  width: 220px; flex-shrink: 0;
  border-left: 1px solid #e8e8e8; background: #fafbfc;
}
.tasks-panel { display: flex; flex-direction: column; height: 100%; padding: 14px; }
.tasks-hd { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.tasks-empty { font-size: 13px; color: #8b949e; }
.suggestions-block {
  margin-bottom: 18px;
}
.suggestion-item {
  padding: 8px 10px;
  margin-bottom: 6px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
  color: #1f2328;
  font-size: 12px;
  line-height: 1.5;
  cursor: pointer;
}
.suggestion-item:hover {
  border-color: #0969da;
  background: #eef5ff;
}
.task-item { display: flex; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.task-status {
  font-size: 16px; flex-shrink: 0; width: 20px; text-align: center;
}
.task-status.done { color: #1a7f37; }
.task-status.running { color: #0969da; animation: pulse 1.2s infinite; }
.task-status.failed { color: #cf222e; }
.task-status.pending { color: #d0d7de; }
.task-goal { font-size: 13px; line-height: 1.4; }
.task-agent { font-size: 11px; color: #8b949e; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Responsive */
.agent-left.is-hidden, .agent-right.is-hidden { display: none; }
@media (max-width: 767px) {
  .agent-left { position: fixed; left: 0; top: 0; bottom: 0; z-index: 50; width: 260px; }
  .agent-right { position: fixed; right: 0; top: 0; bottom: 0; z-index: 50; width: 240px; }
}
</style>
