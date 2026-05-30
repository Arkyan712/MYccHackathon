<script setup lang="ts">
import { ref, computed, onMounted, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ConversationPreview, MessageItem } from '@/types'
import * as messagesApi from '@/api/messages'
import api from '@/api/client'
import ConversationList from '@/components/message/ConversationList.vue'
import ChatWindow from '@/components/message/ChatWindow.vue'

const route = useRoute()
const refreshNotifications = inject<() => void>('refreshNotifications', () => {})

const conversations = ref<ConversationPreview[]>([])
const messages = ref<MessageItem[]>([])
const activeUserId = ref<number | null>(null)
const activeNeedId = ref<number>(0)
// Remember need_id per conversation (userId -> needId)
const needIdMap = ref<Record<number, number>>({})
const loading = ref(false)

const isMobile = ref(window.innerWidth < 768)
const showList = ref(true)

const activeUserName = computed(() =>
  conversations.value.find((c) => c.other_user_id === activeUserId.value)?.other_username || ''
)

const hasActiveConversation = computed(() => activeUserId.value !== null)

function onResize() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  loadConversations()
  window.addEventListener('resize', onResize)
})

watch(
  () => route.params.userId,
  (id) => {
    if (id) {
      const needIdFromQuery = Number(route.query.needId) || 0
      selectConversation(Number(id), needIdFromQuery)
    }
  },
  { immediate: true }
)

async function loadConversations() {
  try {
    const { data } = await messagesApi.getConversations()
    conversations.value = data
  } catch {
    /* ignore */
  }
}

async function selectConversation(userId: number, initialNeedId: number = 0) {
  activeUserId.value = userId
  loading.value = true

  // Restore remembered need_id or use initial
  const remembered = needIdMap.value[userId]
  activeNeedId.value = initialNeedId || remembered || 0

  try {
    const { data } = await messagesApi.getMessages(userId, activeNeedId.value || undefined)
    messages.value = data
    if (data.length > 0 && data[0].need_id) {
      activeNeedId.value = data[0].need_id
      needIdMap.value[userId] = data[0].need_id
    }
  } catch {
    messages.value = []
  } finally {
    loading.value = false
  }

  // If user not in conversation list yet, fetch name and add entry
  if (!conversations.value.find(c => c.other_user_id === userId)) {
    let username = '用户 ' + userId
    try {
      const { data } = await api.get(`/profile/user/${userId}`)
      if (data.username) username = data.username
    } catch { /* use fallback */ }
    conversations.value.unshift({
      other_user_id: userId,
      other_username: username,
      last_message: '',
      last_time: new Date().toISOString(),
    })
  }

  // Mark messages as read
  try { await messagesApi.markRead(userId, activeNeedId.value || undefined) } catch (e: any) { console.error('markRead failed:', e?.response?.status, e?.response?.data || e?.message || e) }
  refreshNotifications()
  if (isMobile.value) {
    showList.value = false
  }
}

function handleBackToList() {
  showList.value = true
}

async function handleSend(content: string) {
  if (!activeUserId.value) return
  try {
    const { data } = await messagesApi.sendMessage({
      need_id: activeNeedId.value,
      receiver_id: activeUserId.value,
      content,
    })
    messages.value.push(data)
    // Remember need_id and refresh conversation list
    if (data.need_id) {
      needIdMap.value[activeUserId.value] = data.need_id
    }
    loadConversations()
  } catch (e: any) {
    ElMessage.error('发送失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  }
}
</script>

<template>
  <div class="messages-page">
    <div class="page-header">
      <h1 class="page-title">站内消息</h1>
    </div>

    <el-card shadow="never" class="messages-card" :body-style="{ padding: '0' }">
      <div class="msg-layout">
        <!-- Left: Conversation List -->
        <div
          class="msg-sidebar"
          :class="{ 'is-active': showList }"
        >
          <ConversationList
            :conversations="conversations"
            :active-id="activeUserId"
            @select="selectConversation"
          />
        </div>

        <!-- Right: Chat Window -->
        <div
          class="msg-main"
          :class="{ 'is-active': !showList || !isMobile }"
        >
          <!-- Mobile back button -->
          <div v-if="isMobile && hasActiveConversation && !showList" class="mobile-back-row">
            <el-button type="primary" link @click="handleBackToList">
              <el-icon><ArrowLeft /></el-icon>
              返回对话列表
            </el-button>
          </div>

          <div v-if="hasActiveConversation" v-loading="loading" class="chat-container">
            <ChatWindow
              :messages="messages"
              :other-name="activeUserName"
              @send="handleSend"
            />
          </div>

          <div v-else class="empty-placeholder">
            <el-empty description="选择一个对话开始聊天" :image-size="80" />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.messages-page {
  padding: 0;
  height: calc(100vh - 56px - 48px);
  display: flex;
  flex-direction: column;
  margin: -24px auto 0;
  max-width: 1000px;
}

.page-header { margin-bottom: 0; flex-shrink: 0; display: none; }
.page-title { font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0; }

/* Card */
.messages-card {
  flex: 1; min-height: 0;
  border: none !important;
  border-radius: 0 !important;
  overflow: hidden;
  box-shadow: none !important;
}
.messages-card :deep(.el-card__body) { height: 100%; }

/* Layout */
.msg-layout { display: flex; height: 100%; }
.msg-sidebar { width: 280px; flex-shrink: 0; border-right: 1px solid var(--card-border); }
.msg-main { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--bg); }

/* Mobile */
.mobile-back-row {
  padding: 12px 16px; border-bottom: 1px solid var(--card-border);
  flex-shrink: 0; background: #fff;
}
.chat-container { flex: 1; min-height: 0; }
.empty-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; }

/* Mobile responsive */
@media (max-width: 767px) {
  .messages-page { padding: 0; height: calc(100vh - 56px - 56px); margin: -16px; }
  .msg-layout { position: relative; }
  .msg-sidebar { width: 100%; display: none; }
  .msg-sidebar.is-active { display: block; }
  .msg-main { display: none; }
  .msg-main.is-active { display: flex; }
}
</style>
