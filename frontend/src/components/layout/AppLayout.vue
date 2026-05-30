<script setup lang="ts">
import { ref, computed, onMounted, watch, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDebugStore } from '@/stores/debug'
import { ElMessage } from 'element-plus'
import api from '@/api/client'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const debug = useDebugStore()
const collapsed = ref(false)
const avatarUploading = ref(false)
const avatarInput = ref<HTMLInputElement>()

function triggerAvatarInput() { avatarInput.value?.click() }

async function handleAvatarUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) { ElMessage.warning('图片不能超过2MB'); return }
  avatarUploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/profile/avatar', form)
    if (auth.user) auth.user = { ...auth.user, avatar: data.avatar }
    ElMessage.success('头像已更新')
  } catch (e: any) {
    console.error('Avatar upload failed:', e?.response?.status, e?.response?.data || e?.message || e)
    ElMessage.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  }
  finally { avatarUploading.value = false }
}

// Notifications
const notifyCount = ref(0)
const notifyItems = ref<{ id: number; sender_name: string; content: string; time: string; need_id: number }[]>([])

async function fetchNotifications() {
  try {
    const { data } = await api.get('/messages/notifications')
    notifyCount.value = data.count
    notifyItems.value = data.items
  } catch (e: any) {
    console.error('Notifications fetch failed:', e?.response?.status, e?.response?.data || e?.message || e)
  }
}
provide('refreshNotifications', fetchNotifications)
onMounted(() => {
  if (auth.token && !auth.user) auth.fetchMe()
  fetchNotifications()
})
watch(() => route.path, () => { fetchNotifications() })

const menuItems = [
  { path: '/',              icon: 'House',      label: '需求广场' },
  { path: '/needs/new',     icon: 'CirclePlus', label: '发布需求' },
  { path: '/needs/manage',  icon: 'List',        label: '我的需求' },
  { path: '/agent',         icon: 'MagicStick',  label: '智能助手' },
  { path: '/messages',      icon: 'ChatDotRound', label: '站内消息' },
  { path: '/profile/setup', icon: 'User',       label: '个人中心' },
  { path: '/settings',      icon: 'Setting',    label: '系统设置' },
]

const activeMenu = computed(() => {
  if (route.path.startsWith('/messages')) return '/messages'
  if (route.path.startsWith('/agent')) return '/agent'
  if (route.path.startsWith('/needs/manage')) return '/needs/manage'
  if (route.path.startsWith('/needs/new')) return '/needs/new'
  if (route.path.startsWith('/needs/')) return '/'
  if (route.path.startsWith('/settings')) return '/settings'
  if (route.path.startsWith('/profile')) return '/profile/setup'
  return '/'
})

const pageTitle = computed(() => {
  if (route.path.includes('needs/new')) return '发布需求'
  if (route.path.includes('matches')) return '匹配结果'
  if (route.path.includes('messages')) return '站内消息'
  if (route.path.includes('profile')) return '个人中心'
  return '需求广场'
})

function go(p: string) { router.push(p) }

function handleLogout() {
  auth.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}
</script>

<template>
  <div class="app-container">
    <!-- Sidebar -->
    <aside class="app-sidebar" :class="{ collapsed }">
      <div class="sidebar-logo" @click="go('/')">
        <span class="logo-text">AI Campus</span>
      </div>

      <div class="sidebar-menu">
        <div
          v-for="m in menuItems"
          :key="m.path"
          class="menu-item"
          :class="{ active: activeMenu === m.path }"
          @click="go(m.path)"
        >
          <el-icon :size="18"><component :is="m.icon" /></el-icon>
          <span class="menu-label">{{ m.label }}</span>
        </div>
      </div>

      <div class="sidebar-user">
        <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="handleAvatarUpload" />
        <el-dropdown trigger="click" placement="right-end">
          <div class="user-area">
            <el-avatar :size="32" :src="auth.user?.avatar" icon="UserFilled" />
            <div v-if="!collapsed" class="user-info">
              <div class="user-name">{{ auth.user?.username }}</div>
              <div class="user-role">安州区</div>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="go('/profile/setup')">
                <el-icon><User /></el-icon> 个人中心
              </el-dropdown-item>
              <el-dropdown-item @click="triggerAvatarInput">
                <el-icon><Camera /></el-icon> 更换头像
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- Main -->
    <main class="app-main">
      <div class="main-topbar">
        <div class="topbar-left">
          <el-button text class="collapse-btn" @click="collapsed = !collapsed">
            <el-icon :size="18"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click" placement="bottom-end">
            <el-badge :value="notifyCount" :max="99" :hidden="notifyCount === 0" class="topbar-badge">
              <el-button text><el-icon :size="18"><Bell /></el-icon></el-button>
            </el-badge>
            <template #dropdown>
              <el-dropdown-menu>
                <div class="notify-dropdown">
                  <div class="notify-hd">消息通知</div>
                  <div v-if="notifyItems.length === 0" class="notify-empty">暂无消息</div>
                  <div v-for="n in notifyItems" :key="n.id" class="notify-item" @click="go(`/needs/${n.need_id}/matches`)">
                    <div class="notify-sender">{{ n.sender_name }}</div>
                    <div class="notify-content">{{ n.content }}</div>
                    <div class="notify-time">{{ n.time.slice(5, 16) }}</div>
                  </div>
                  <div v-if="notifyItems.length" class="notify-ft" @click="go('/messages')">查看全部消息 →</div>
                </div>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <div class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- Debug event panel -->
    <div class="debug-panel" :class="{ collapsed: !debug.visible }">
      <div class="debug-header" @click="debug.toggle()">
        <span>Events ({{ debug.events.length }})</span>
        <el-button size="small" text @click.stop="debug.clear()">清空</el-button>
      </div>
      <div v-if="debug.visible" class="debug-body">
        <div v-for="e in [...debug.events].reverse().slice(0, 8)" :key="e.id" class="debug-event" :class="e.type">
          <span class="debug-time">{{ e.time }}</span>
          <span class="debug-msg">{{ e.message }}</span>
        </div>
        <div v-if="debug.events.length === 0" class="debug-empty">暂无事件，操作页面即可看到</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-container { display: flex; height: 100vh; overflow: hidden; }

/* === Sidebar === */
.app-sidebar {
  width: 220px; background: #001529; display: flex; flex-direction: column;
  transition: width 0.2s; flex-shrink: 0; overflow: hidden;
  position: relative;
}
.app-sidebar.collapsed { width: 64px; }

.sidebar-logo {
  height: 56px; display: flex; align-items: center; justify-content: center;
  cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-text { color: #fff; font-size: 16px; font-weight: 700; white-space: nowrap; }

/* Menu Items */
.sidebar-menu { flex: 1; padding: 8px; }
.menu-item {
  display: flex; align-items: center; gap: 10px;
  height: 44px; padding: 0 16px; margin-bottom: 2px;
  border-radius: 6px; cursor: pointer; transition: all 0.15s;
  color: rgba(255,255,255,0.65); font-size: 14px;
}
.menu-item:hover { color: #fff; background: rgba(255,255,255,0.08); }
.menu-item.active { color: #fff; background: #0969da; }
.menu-label { white-space: nowrap; overflow: hidden; }

/* User Area */
.sidebar-user {
  padding: 12px; border-top: 1px solid rgba(255,255,255,0.08);
}
.user-area {
  display: flex; align-items: center; gap: 10px; cursor: pointer;
  padding: 4px; border-radius: 6px; transition: background 0.15s;
}
.user-area:hover { background: rgba(255,255,255,0.08); }
.user-info { overflow: hidden; }
.user-name { color: #fff; font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.user-role { color: rgba(255,255,255,0.45); font-size: 12px; }

/* === Main === */
.app-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.main-topbar {
  height: 48px; background: #fff; display: flex; align-items: center;
  justify-content: space-between; padding: 0 16px;
  border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0,21,41,0.05);
}
.topbar-left, .topbar-right { display: flex; align-items: center; gap: 8px; }
.collapse-btn { padding: 4px; }
.main-content { flex: 1; overflow-y: auto; padding: 24px; }

/* Bell animation */
.topbar-badge :deep(.el-button:hover svg) {
  animation: bell-shake 0.3s ease-in-out;
}
@keyframes bell-shake {
  0%, 100% { transform: rotate(0); }
  25% { transform: rotate(10deg); }
  75% { transform: rotate(-10deg); }
}

/* Notification dropdown */
.notify-dropdown { width: 300px; max-height: 360px; overflow-y: auto; }
.notify-hd { padding: 12px 16px; font-weight: 600; font-size: 14px; border-bottom: 1px solid #f0f0f0; }
.notify-empty { padding: 24px; text-align: center; color: rgba(0,0,0,0.25); font-size: 13px; }
.notify-item { padding: 10px 16px; border-bottom: 1px solid #f5f5f5; cursor: pointer; }
.notify-item:hover { background: #f6f8fa; }
.notify-sender { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
.notify-content { font-size: 12px; color: rgba(0,0,0,0.45); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notify-time { font-size: 11px; color: rgba(0,0,0,0.25); margin-top: 2px; }
.notify-ft { padding: 10px 16px; text-align: center; font-size: 13px; color: #0969da; cursor: pointer; border-top: 1px solid #f0f0f0; }
.notify-ft:hover { background: #f6f8fa; }

/* Debug panel */
.debug-panel {
  position: fixed; bottom: 0; right: 0; width: 320px;
  background: #1a1a2e; color: #e0e0e0; z-index: 1000;
  border-radius: 8px 0 0 0; font-size: 12px;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.3);
  transition: max-height 0.2s;
  max-height: 300px; overflow: hidden;
}
.debug-panel.collapsed { max-height: 32px; }
.debug-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #333;
  font-weight: 600; font-size: 12px;
}
.debug-header .el-button { color: #aaa; font-size: 11px; }
.debug-body { padding: 4px 10px 8px; max-height: 240px; overflow-y: auto; }
.debug-event {
  display: flex; gap: 8px; padding: 3px 0; border-bottom: 1px solid #2a2a3e;
  align-items: baseline;
}
.debug-time { color: #666; flex-shrink: 0; font-size: 11px; }
.debug-msg { word-break: break-all; }
.debug-event.success .debug-msg { color: #57ab5a; }
.debug-event.error .debug-msg { color: #e5534b; }
.debug-event.api .debug-msg { color: #58a6ff; }
.debug-event.info .debug-msg { color: #8b949e; }
.debug-empty { color: #666; text-align: center; padding: 8px; }

/* Responsive */
@media (max-width: 768px) {
  .app-sidebar { position: fixed; left: 0; top: 0; bottom: 0; z-index: 100; transform: translateX(0); }
  .app-sidebar.collapsed { transform: translateX(-100%); width: 220px; }
  .main-content { padding: 16px; }
}
</style>
