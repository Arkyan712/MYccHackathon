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
const isMobile = ref(window.innerWidth < 768)
const activeSessionId = ref<number | null>(null)
const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)

onMounted(async () => {
  await store.fetchSessions()
  const sid = route.params.sessionId
  if (sid) {
    activeSessionId.value = Number(sid)
    await store.loadSession(Number(sid))
  } else if (store.sessions.length > 0) {
    const latest = store.sessions[0]
    router.replace(`/agent/${latest.id}`)
  }
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
  try { await ElMessageBox.confirm('确定删除这个会话吗？', '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }) }
  catch { return }
  try {
    await store.deleteSession(id)
    if (activeSessionId.value === id) { activeSessionId.value = null; router.push('/agent') }
    ElMessage.success('已删除')
  } catch (e: any) { ElMessage.error('删除失败: ' + (e?.response?.data?.detail || e?.message || '')) }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || !activeSessionId.value) return
  inputText.value = ''
  if (text.startsWith('/plan ')) { await store.triggerPlan(activeSessionId.value, text.slice(6)) }
  else { await store.sendMessage(activeSessionId.value, text) }
  scrollToBottom()
}

async function handleFileUpload(file: File) {
  if (!activeSessionId.value) { ElMessage.warning('请先创建一个会话'); return }
  uploading.value = true
  ElMessage.info(`正在上传并分析 ${file.name}...`)
  try { await store.uploadFile(activeSessionId.value, file); ElMessage.success(`${file.name} 分析完成！`) }
  catch (e: any) { ElMessage.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '未知错误')) }
  finally { uploading.value = false; scrollToBottom() }
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
          <div v-for="s in store.sessions" :key="s.id" class="session-item" :class="{ active: s.id === activeSessionId }" @click="handleSelectSession(s.id)">
            <div class="session-info">
              <div class="session-title">{{ s.title }}</div>
              <div class="session-date">{{ s.updated_at?.slice(0, 16) }}</div>
            </div>
            <el-button size="small" text type="danger" @click.stop="handleDeleteSession(s.id)">×</el-button>
          </div>
          <el-empty v-if="store.sessions.length === 0" description="暂无会话" :image-size="40" />
        </div>
      </div>
    </div>

    <!-- Center: Chat -->
    <div class="agent-center">
      <div class="chat-panel">
        <div class="chat-topbar">
          <el-button v-if="isMobile" text @click="showSessions = !showSessions">会话</el-button>
          <span class="chat-title">{{ store.currentSession?.title || 'AI 智能助手' }}</span>
          <div v-if="store.suggestions.length" class="suggestions-bar">
            <span v-for="s in store.suggestions.slice(0, 3)" :key="s" class="suggestion-chip" @click="inputText = s">{{ s }}</span>
          </div>
        </div>

        <div class="chat-messages" v-loading="store.loading">
          <el-empty v-if="store.messages.length === 0 && !store.loading" description="我是你的 AI 助手，可以帮你分析文件、发布需求、查看匹配结果。上传一个文件试试吧！" :image-size="48" />

          <div v-for="m in store.messages" :key="m.id" class="chat-msg" :class="m.role">
            <div class="msg-avatar">{{ m.role === 'user' ? '我' : m.role === 'assistant' ? 'AI' : '!' }}</div>
            <div class="msg-bubble" :class="m.role">
              <div class="msg-content">{{ m.content }}</div>
              <div v-if="getMessageDrafts(m).length" class="draft-preview">
                <div v-for="(d, di) in getMessageDrafts(m)" :key="di" class="draft-card">
                  <div class="draft-top"><el-tag size="small" effect="plain">{{ d.type }}</el-tag><span class="draft-mode">{{ d.selection_mode === 'multi' ? '多选' : '单选' }}</span></div>
                  <strong>{{ d.title }}</strong>
                  <p>{{ d.description?.slice(0, 80) }}{{ d.description?.length > 80 ? '...' : '' }}</p>
                </div>
                <el-button type="primary" size="small" @click="handlePublishDrafts(getMessageDrafts(m))">确认发布</el-button>
              </div>
            </div>
          </div>

          <!-- Tasks progress -->
          <div v-if="store.tasks.length > 0" class="tasks-inline">
            <div v-for="t in store.tasks" :key="t.id" class="task-row">
              <span class="task-dot" :class="t.status">{{ t.status === 'done' ? '✓' : t.status === 'running' ? '●' : '○' }}</span>
              <span class="task-goal">{{ t.goal }}</span>
            </div>
          </div>
        </div>

        <div class="chat-input-bar">
          <input ref="fileInput" type="file" accept=".txt,.docx,.pdf" style="display:none" @change="(e) => { const el = e.target as HTMLInputElement; const f = el.files?.[0]; if (f) { handleFileUpload(f).finally(() => { el.value = '' }) } }" />
          <el-button text class="upload-btn" :loading="uploading" @click="fileInput?.click()">{{ uploading ? '⏳' : '📎' }}</el-button>
          <el-input v-model="inputText" placeholder="输入消息，或输入 /plan 目标 来制定计划..." :disabled="store.isStreaming" @keyup.enter="handleSend" class="chat-input" />
          <el-button type="primary" :disabled="!inputText.trim() || store.isStreaming" @click="handleSend">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-view { display: flex; height: calc(100vh - 56px - 48px); overflow: hidden; margin: -24px; }

/* -- Left: Sessions -- */
.agent-left { width: 280px; flex-shrink: 0; border-right: 1px solid var(--card-border); background: linear-gradient(180deg, #fafbfc 0%, #fff 100%); }
.agent-left::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(180deg, transparent 0%, var(--card-border) 20%, var(--card-border) 80%, transparent 100%);
}
.sessions-panel { display: flex; flex-direction: column; height: 100%; }
.sessions-hd { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid var(--card-border); }
.sessions-title { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.sessions-list { flex: 1; overflow-y: auto; padding: 8px; }
.session-item { 
  position: relative;
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  padding: 12px 14px; 
  border-radius: var(--radius-md); 
  cursor: pointer; 
  margin-bottom: 4px; 
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.session-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: var(--primary-gradient);
  border-radius: 0 2px 2px 0;
  transition: height 0.3s ease;
}
.session-item:hover::before,
.session-item.active::before {
  height: 60%;
}
.session-item:hover { 
  background: var(--primary-light);
  transform: translateX(4px);
}
.session-item.active { 
  background: linear-gradient(90deg, var(--primary-light) 0%, transparent 100%);
  border: 1px solid var(--primary);
}
.session-info { flex: 1; min-width: 0; }
.session-title { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary); }
.session-date { font-size: 11px; color: var(--text-muted); margin-top: 3px; }

/* -- Center: Chat -- */
.agent-center { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-panel { display: flex; flex-direction: column; height: 100%; }
.chat-topbar { display: flex; align-items: center; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--card-border); background: #fff; }
.chat-title { font-size: 15px; font-weight: 700; color: var(--text-primary); white-space: nowrap; }
.suggestions-bar { display: flex; gap: 6px; overflow-x: auto; flex: 1; min-width: 0; }
.suggestion-chip { font-size: 11px; color: var(--primary); background: var(--primary-light); padding: 4px 10px; border-radius: var(--radius-full); white-space: nowrap; cursor: pointer; transition: all var(--transition-fast); flex-shrink: 0; }
.suggestion-chip:hover { background: var(--primary); color: #fff; }

.chat-messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; background: linear-gradient(180deg, var(--bg) 0%, rgba(126, 172, 204, 0.03) 100%); }

.chat-msg { display: flex; gap: 12px; max-width: 85%; }
.chat-msg.user { align-self: flex-end; flex-direction: row-reverse; }
.chat-msg.assistant, .chat-msg.system { align-self: flex-start; }

.msg-avatar { 
  width: 34px; 
  height: 34px; 
  border-radius: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  font-size: 12px; 
  font-weight: 700; 
  flex-shrink: 0;
  transition: transform 0.2s ease;
}
.chat-msg:hover .msg-avatar {
  transform: scale(1.05);
}
.chat-msg.user .msg-avatar { 
  background: var(--primary-gradient); 
  color: #fff;
  box-shadow: 0 2px 8px rgba(126, 172, 204, 0.3);
}
.chat-msg.assistant .msg-avatar { 
  background: var(--accent-light); 
  color: var(--accent-hover);
  box-shadow: 0 2px 8px rgba(109, 179, 212, 0.2);
}
.chat-msg.system .msg-avatar { 
  background: linear-gradient(135deg, #FEF3C7, #FDE68A); 
  color: #92400E;
}

.msg-bubble { 
  position: relative;
  padding: 14px 18px; 
  border-radius: var(--radius-lg); 
  font-size: 14px; 
  line-height: 1.7;
  backdrop-filter: blur(10px);
}
.chat-msg.user .msg-bubble { 
  background: var(--primary-gradient); 
  color: #fff; 
  border-bottom-right-radius: 6px;
  box-shadow: 0 4px 16px rgba(126, 172, 204, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.15);
}
.chat-msg.assistant .msg-bubble { 
  background: #fff; 
  border: 1px solid rgba(126, 172, 204, 0.12); 
  border-bottom-left-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.chat-msg.system .msg-bubble { 
  background: linear-gradient(90deg, rgba(126, 172, 204, 0.08) 0%, rgba(126, 172, 204, 0.04) 100%); 
  border: 1px solid rgba(126, 172, 204, 0.15); 
  font-size: 13px;
}

/* Message tail */
.msg-bubble::after {
  content: '';
  position: absolute;
  bottom: 0;
  width: 12px;
  height: 12px;
  background: inherit;
  border: inherit;
}
.chat-msg.user .msg-bubble::after {
  right: -6px;
  border-radius: 0 0 0 12px;
  border-right: none;
  border-top: none;
}
.chat-msg.assistant .msg-bubble::after {
  left: -6px;
  border-radius: 0 0 12px 0;
  border-left: none;
  border-top: none;
}

.msg-content { word-break: break-word; white-space: pre-wrap; }

/* -- Draft preview -- */
.draft-preview { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.draft-card { 
  background: linear-gradient(135deg, var(--primary-light) 0%, rgba(126, 172, 204, 0.06) 100%); 
  border: 1px solid rgba(126, 172, 204, 0.15); 
  border-radius: var(--radius-md); 
  padding: 14px;
  transition: all 0.2s ease;
}
.draft-card:hover {
  border-color: var(--primary);
  transform: translateX(4px);
}
.draft-card p { font-size: 13px; color: var(--text-secondary); margin: 6px 0 0; line-height: 1.5; }
.draft-top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.draft-mode { font-size: 12px; color: var(--text-muted); padding: 2px 8px; background: var(--bg-surface); border-radius: var(--radius-sm); }

/* -- Tasks inline -- */
.tasks-inline { align-self: flex-start; display: flex; flex-direction: column; gap: 8px; padding: 10px 16px; background: rgba(126, 172, 204, 0.06); border-radius: var(--radius-md); border: 1px solid rgba(126, 172, 204, 0.1); }
.task-row { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-secondary); }
.task-dot { font-weight: 700; font-size: 14px; }
.task-dot.done { color: var(--success); }
.task-dot.running { color: var(--primary); animation: pulse 1.5s ease-in-out infinite; }
.task-dot.failed { color: var(--danger); }
@keyframes pulse { 0%,100%{opacity:1; transform: scale(1)} 50%{opacity:0.5; transform: scale(1.1)} }

/* -- Input -- */
.chat-input-bar { 
  display: flex; 
  align-items: center; 
  gap: 10px; 
  padding: 14px 16px; 
  border-top: 1px solid var(--card-border); 
  background: #fff;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
}
.chat-input { flex: 1; }
.upload-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
}
.upload-btn:hover {
  background: var(--primary-light);
  transform: scale(1.05);
}

/* -- Responsive -- */
.agent-left.is-hidden { display: none; }
@media (max-width: 767px) {
  .agent-left { position: fixed; left: 0; top: 0; bottom: 0; z-index: 50; width: 260px; }
  .suggestions-bar { display: none; }
}
</style>
