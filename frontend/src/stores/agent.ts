import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AgentSession, AgentMessage, AgentTask, NeedDraft } from '@/types'
import * as agentApi from '@/api/agent'
import { useDebugStore } from '@/stores/debug'

export const useAgentStore = defineStore('agent', () => {
  const debug = useDebugStore()
  const sessions = ref<{ id: number; title: string; status: string; summary?: string; created_at: string; updated_at: string }[]>([])
  const currentSession = ref<AgentSession | null>(null)
  const messages = ref<AgentMessage[]>([])
  const tasks = ref<AgentTask[]>([])
  const suggestions = ref<string[]>([])
  const isStreaming = ref(false)
  const loading = ref(false)

  async function fetchSessions() {
    try {
      const { data } = await agentApi.listSessions()
      sessions.value = data
    } catch { /* ignore */ }
  }

  async function createSession(title?: string) {
    const { data } = await agentApi.createSession(title)
    await fetchSessions()
    return data.id
  }

  async function loadSession(id: number) {
    loading.value = true
    try {
      const { data } = await agentApi.getSession(id)
      currentSession.value = data.session as AgentSession
      messages.value = data.messages as AgentMessage[]
      tasks.value = data.tasks as AgentTask[]
      await fetchSuggestions(id)
    } catch { /* ignore */ }
    finally { loading.value = false }
  }

  async function refreshTasks(sessionId: number) {
    const { data } = await agentApi.getTasks(sessionId)
    tasks.value = data as AgentTask[]
  }

  async function deleteSession(id: number) {
    await agentApi.deleteSession(id)
    await fetchSessions()
  }

  async function sendMessage(sessionId: number, content: string) {
    isStreaming.value = true
    debug.api(`Agent 消息 → session ${sessionId}`)
    messages.value.push({
      id: Date.now(), session_id: sessionId, role: 'user',
      content, created_at: new Date().toISOString(),
    })
    try {
      const { data } = await agentApi.sendMessage(sessionId, content)
      messages.value.push({
        id: Date.now() + 1, session_id: sessionId, role: 'assistant',
        content: data.reply,
        extra_metadata: data.drafts ? { drafts: data.drafts } : undefined,
        created_at: new Date().toISOString(),
      })
      if (data.drafts) {
        // Store drafts for UI to show preview
        if (currentSession.value) {
          currentSession.value = {
            ...currentSession.value,
            planning_state: { phase: 'drafts_ready', drafts: data.drafts },
          }
        }
      }
      return data
    } catch {
      messages.value.push({
        id: Date.now() + 1, session_id: sessionId, role: 'system',
        content: '抱歉，AI回复出错了，请重试。',
        created_at: new Date().toISOString(),
      })
    } finally {
      isStreaming.value = false
    }
  }

  async function uploadFile(sessionId: number, file: File) {
    isStreaming.value = true
    try {
      const { data } = await agentApi.uploadFile(sessionId, file)
      messages.value.push({
        id: Date.now() + 1, session_id: sessionId, role: 'assistant',
        content: data.reply,
        extra_metadata: { file_id: data.file_id, extracted: data.extracted, drafts: data.drafts },
        created_at: new Date().toISOString(),
      })
      await refreshTasks(sessionId)
      return data
    } finally {
      isStreaming.value = false
    }
  }

  async function triggerPlan(sessionId: number, goal: string) {
    try {
      const { data } = await agentApi.triggerPlan(sessionId, goal)
      messages.value.push({
        id: Date.now() + 1, session_id: sessionId, role: 'system',
        content: data.reply,
        extra_metadata: { type: 'plan' },
        created_at: new Date().toISOString(),
      })
      if (data.tasks) tasks.value = data.tasks as AgentTask[]
      await refreshTasks(sessionId)
      return data
    } catch { /* ignore */ }
  }

  async function confirmPublish(sessionId: number, drafts: NeedDraft[]) {
    try {
      const { data } = await agentApi.confirmPublish(sessionId, drafts)
      messages.value.push({
        id: Date.now() + 1, session_id: sessionId, role: 'system',
        content: data.reply,
        extra_metadata: { type: 'publish_done' },
        created_at: new Date().toISOString(),
      })
      await refreshTasks(sessionId)
      await fetchSuggestions(sessionId)
      return data
    } catch { /* ignore */ }
  }

  async function fetchSuggestions(sessionId: number) {
    try {
      const { data } = await agentApi.getSuggestions(sessionId)
      suggestions.value = data.suggestions
    } catch {
      suggestions.value = []
    }
  }

  return {
    sessions, currentSession, messages, tasks, suggestions, isStreaming, loading,
    fetchSessions, createSession, loadSession, deleteSession,
    sendMessage, uploadFile, triggerPlan, confirmPublish, fetchSuggestions, refreshTasks,
  }
})
