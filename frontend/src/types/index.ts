export interface User {
  id: number
  username: string
  avatar?: string
  bio?: string
  skill_tags?: string[]
  school?: string
  extra?: Record<string, unknown> | string
  rating_score: number
  created_at: string
}

export interface Need {
  id: number
  user_id: number
  username: string
  type: '求助' | '组队' | '技能交换'
  title: string
  description: string
  req_tags?: string[]
  selection_mode: 'single' | 'multi'
  selected_user_ids?: number[]
  status: '开放' | '已匹配' | '关闭'
  created_at: string
}

export interface AgentSession {
  id: number
  user_id: number
  title: string
  summary?: string
  planning_state?: Record<string, unknown>
  status: string
  created_at: string
  updated_at: string
}

export interface AgentMessage {
  id: number
  session_id: number
  role: string
  content: string
  token_count?: number
  extra_metadata?: Record<string, unknown>
  created_at: string
}

export interface AgentTask {
  id: number
  session_id: number
  parent_task_id?: number
  goal: string
  status: string
  assigned_agent?: string
  result?: Record<string, unknown>
  error?: string
  children?: AgentTask[]
  created_at: string
}

export interface NeedDraft {
  type: string
  title: string
  description: string
  selection_mode?: string
}

export interface MatchResult {
  user_id: number
  score: number
  reason: string
  complementarity?: string
  username: string
  school: string
  bio?: string
  extra?: Record<string, unknown>
  skill_tags: string[]
}

export interface MatchProgress {
  stage: 'tag_extraction' | 'semantic_search' | 'rerank' | 'done' | 'error'
  message: string
  data?: Record<string, unknown>
}

export interface MessageItem {
  id: number
  need_id: number
  sender_id: number
  receiver_id: number
  content: string
  created_at: string
}

export interface ConversationPreview {
  other_user_id: number
  other_username: string
  last_message: string
  last_time: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}
