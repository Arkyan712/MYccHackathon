import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Need, MatchResult, MatchProgress } from '@/types'
import * as needsApi from '@/api/needs'
import { useAuthStore } from './auth'

export const useNeedsStore = defineStore('needs', () => {
  const needs = ref<Need[]>([])
  const total = ref(0)
  const currentNeed = ref<Need | null>(null)
  const matches = ref<MatchResult[]>([])
  const matchProgress = ref<MatchProgress[]>([])
  const loading = ref(false)
  let activeEventSource: EventSource | null = null
  let sseErrorCount = 0

  async function fetchNeeds(params?: { page?: number; page_size?: number; status?: string; type?: string }) {
    loading.value = true
    try {
      const { data } = await needsApi.getNeeds(params)
      needs.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function createNeed(payload: { type: string; title: string; description: string; selection_mode?: string }) {
    const { data } = await needsApi.createNeed(payload)
    currentNeed.value = data
    return data
  }

  async function fetchMatches(needId: number) {
    loading.value = true
    try {
      const { data } = await needsApi.getMatches(needId)
      currentNeed.value = data.need
      matches.value = data.matches
    } finally {
      loading.value = false
    }
  }

  function streamMatches(needId: number) {
    if (activeEventSource) {
      activeEventSource.close()
    }
    sseErrorCount = 0
    matchProgress.value = []
    matches.value = []

    const authStore = useAuthStore()
    const url = needsApi.getMatchStreamUrl(needId) + `?token=${encodeURIComponent(authStore.token || '')}`
    const eventSource = new EventSource(url)
    activeEventSource = eventSource

    // 60s timeout to prevent indefinite wait
    const timeout = setTimeout(() => {
      if (eventSource.readyState !== EventSource.CLOSED) {
        eventSource.close()
        matchProgress.value.push({ stage: 'error', message: '匹配超时，请点击刷新重试' })
      }
    }, 60000)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as MatchProgress
        matchProgress.value.push(data)
        if (data.stage === 'done' && data.data?.results) {
          matches.value = data.data.results as MatchResult[]
          clearTimeout(timeout)
          eventSource.close()
        }
        if (data.stage === 'error') {
          clearTimeout(timeout)
          eventSource.close()
        }
      } catch {
        matchProgress.value.push({ stage: 'error', message: '数据解析失败' })
        clearTimeout(timeout)
        eventSource.close()
      }
    }

    eventSource.onerror = () => {
      sseErrorCount++
      if (sseErrorCount >= 3 || eventSource.readyState === EventSource.CLOSED) {
        clearTimeout(timeout)
        eventSource.close()
        matchProgress.value.push({ stage: 'error', message: '连接失败，请点击刷新重试' })
      }
    }

    return eventSource
  }

  async function refreshMatches(needId: number) {
    loading.value = true
    matchProgress.value = []
    try {
      const { data } = await needsApi.refreshMatches(needId)
      currentNeed.value = data.need
      matches.value = data.matches
    } finally {
      loading.value = false
    }
  }

  async function submitFeedback(matchId: number, feedback: number) {
    await needsApi.submitFeedback(matchId, feedback)
  }

  async function refineNeed(needId: number) {
    const { data } = await needsApi.refineNeed(needId)
    return data.question
  }

  async function logBehavior(event: string, extra?: { target_user_id?: number; need_id?: number }) {
    await needsApi.logBehavior({ event_type: event, ...extra })
  }

  return {
    needs, total, currentNeed, matches, matchProgress, loading,
    fetchNeeds, createNeed, fetchMatches, streamMatches, refreshMatches,
    submitFeedback, refineNeed, logBehavior,
  }
})
