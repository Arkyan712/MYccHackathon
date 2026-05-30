<script setup lang="ts">
import { ref, computed, onMounted, watch, provide, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDebugStore } from '@/stores/debug'
import { ElMessage } from 'element-plus'
import { Bell, User, Setting, SwitchButton, Camera } from '@element-plus/icons-vue'
import api from '@/api/client'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const debug = useDebugStore()
const avatarUploading = ref(false)
const avatarInput = ref<HTMLInputElement>()
const scrolled = ref(false)

let scrollEl: HTMLElement | null = null
function onScroll() {
  if (!scrollEl) scrollEl = document.querySelector('.main-content')
  scrolled.value = (scrollEl?.scrollTop || 0) > 10
}
onMounted(() => {
  setTimeout(() => {
    scrollEl = document.querySelector('.main-content')
    scrollEl?.addEventListener('scroll', onScroll, { passive: true })
  }, 500)
})
onUnmounted(() => { scrollEl?.removeEventListener('scroll', onScroll) })

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
    ElMessage.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally { avatarUploading.value = false }
}

// Notifications
const notifyCount = ref(0)
const notifyItems = ref<{ id: number; sender_name: string; content: string; time: string; need_id: number }[]>([])

async function fetchNotifications() {
  try {
    const { data } = await api.get('/messages/notifications')
    notifyCount.value = data.count
    notifyItems.value = data.items
  } catch { /* ignore */ }
}
provide('refreshNotifications', fetchNotifications)
onMounted(() => {
  if (auth.token && !auth.user) auth.fetchMe()
  fetchNotifications()
})
watch(() => route.path, () => { fetchNotifications() })

const navItems = [
  { path: '/plaza',        icon: 'House',        label: '广场' },
  { path: '/needs/new',    icon: 'CirclePlus',   label: '发布' },
  { path: '/messages',     icon: 'ChatDotRound',  label: '消息' },
  { path: '/agent',        icon: 'MagicStick',    label: 'AI助手' },
  { path: '/profile/setup',icon: 'User',          label: '我的' },
]

const activeNav = computed(() => {
  if (route.path.startsWith('/messages')) return '/messages'
  if (route.path.startsWith('/agent')) return '/agent'
  if (route.path.startsWith('/needs/manage')) return '/profile/setup'
  if (route.path.startsWith('/needs/new')) return '/needs/new'
  if (route.path.startsWith('/needs/')) return '/plaza'
  if (route.path.startsWith('/settings')) return '/profile/setup'
  if (route.path.startsWith('/profile')) return '/profile/setup'
  return '/plaza'
})

function go(p: string) { router.push(p) }
function handleLogout() {
  auth.logout()
  router.push('/login')
  ElMessage.success('已退出登录')
}
</script>

<template>
  <div class="app-shell">
    <!-- ════ Top Navbar ════ -->
    <header class="navbar" :class="{ scrolled }">
      <div class="navbar-inner">
        <div class="navbar-brand" @click="go('/plaza')">
          <span class="brand-icon">🎓</span>
          <span class="brand-text">AI Campus</span>
        </div>

        <!-- Desktop Nav Pills -->
        <nav class="navbar-nav">
          <button
            v-for="item in navItems"
            :key="item.path"
            class="nav-pill"
            :class="{ active: activeNav === item.path }"
            @click="go(item.path)"
          >
            <el-icon :size="16"><component :is="item.icon" /></el-icon>
            <span class="nav-label">{{ item.label }}</span>
          </button>
        </nav>

        <!-- Right actions -->
        <div class="navbar-actions">
          <!-- Notifications -->
          <el-popover placement="bottom-end" :width="320" trigger="click" :offset="8" popper-class="notify-popover">
            <template #reference>
              <el-badge :value="notifyCount" :max="99" :hidden="notifyCount === 0">
                <button class="icon-btn">
                  <el-icon :size="18"><Bell /></el-icon>
                </button>
              </el-badge>
            </template>
            <div class="notify-panel">
              <div class="notify-hd">消息通知</div>
              <div v-if="notifyItems.length === 0" class="notify-empty">暂无消息</div>
              <div v-for="n in notifyItems" :key="n.id" class="notify-item" @click="go(`/needs/${n.need_id}/matches`)">
                <div class="notify-sender">{{ n.sender_name }}</div>
                <div class="notify-content">{{ n.content }}</div>
                <div class="notify-time">{{ n.time.slice(5, 16) }}</div>
              </div>
              <div v-if="notifyItems.length" class="notify-ft" @click="go('/messages')">查看全部消息 →</div>
            </div>
          </el-popover>

          <!-- User -->
          <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="handleAvatarUpload" />
          <el-popover placement="bottom-end" :width="200" trigger="click" :offset="8" popper-class="user-popover">
            <template #reference>
              <button class="user-btn">
                <el-avatar :size="30" :src="auth.user?.avatar" icon="UserFilled" />
                <span class="user-name">{{ auth.user?.username }}</span>
              </button>
            </template>
            <div class="user-menu">
              <div class="user-menu-item" @click="go('/profile/setup')">
                <el-icon :size="16"><User /></el-icon> 个人中心
              </div>
              <div class="user-menu-item" @click="go('/needs/manage')">
                <el-icon :size="16"><Setting /></el-icon> 我的需求
              </div>
              <div class="user-menu-item" @click="go('/settings')">
                <el-icon :size="16"><Setting /></el-icon> 系统设置
              </div>
              <div class="user-menu-item" @click="triggerAvatarInput()">
                <el-icon :size="16"><Camera /></el-icon> 更换头像
              </div>
              <div class="user-menu-divider" />
              <div class="user-menu-item danger" @click="handleLogout()">
                <el-icon :size="16"><SwitchButton /></el-icon> 退出登录
              </div>
            </div>
          </el-popover>
        </div>
      </div>
    </header>

    <!-- ════ Main Content ════ -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- ════ Mobile Bottom Tabs ════ -->
    <nav class="mobile-tabs">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="tab-item"
        :class="{ active: activeNav === item.path }"
        @click="go(item.path)"
      >
        <el-badge v-if="item.path === '/messages'" :value="notifyCount" :max="9" :hidden="notifyCount === 0">
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
        </el-badge>
        <el-icon v-else :size="20"><component :is="item.icon" /></el-icon>
        <span class="tab-label">{{ item.label }}</span>
      </button>
    </nav>

    <!-- ════ Debug Panel ════ -->
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
/* ════ Shell ════ */
.app-shell { display: flex; flex-direction: column; height: 100vh; overflow: hidden; background: var(--bg); }

/* ════ Navbar ════ */
.navbar {
  height: 56px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border-bottom: 1px solid var(--card-border);
  transition: box-shadow var(--transition-normal);
  z-index: 100;
}
.navbar.scrolled { box-shadow: 0 1px 8px rgba(0, 0, 0, 0.06); }

.navbar-inner {
  max-width: 1200px; margin: 0 auto; height: 100%;
  display: flex; align-items: center; padding: 0 24px; gap: 8px;
}

/* Brand */
.navbar-brand { display: flex; align-items: center; gap: 8px; cursor: pointer; flex-shrink: 0; margin-right: 8px; }
.brand-icon { font-size: 22px; }
.brand-text { font-size: 18px; font-weight: 800; background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.3px; }

/* Nav Pills — Desktop */
.navbar-nav { display: flex; align-items: center; gap: 2px; flex: 1; justify-content: center; }
.nav-pill {
  display: flex; align-items: center; gap: 6px; padding: 8px 18px;
  border-radius: var(--radius-full); border: none; background: transparent;
  color: var(--text-secondary); font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all var(--transition-fast); white-space: nowrap;
}
.nav-pill:hover { color: var(--primary); background: var(--primary-light); }
.nav-pill.active {
  color: var(--text-inverse);
  background: var(--primary-gradient);
  box-shadow: var(--primary-glow);
}
.nav-label { font-size: 13px; }

/* Right Actions */
.navbar-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.icon-btn {
  width: 36px; height: 36px; border-radius: 50%; border: none;
  background: transparent; color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.icon-btn:hover { background: var(--primary-light); color: var(--primary); }

.user-btn {
  display: flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px;
  border-radius: var(--radius-full); border: 1px solid transparent;
  background: transparent; cursor: pointer; transition: all var(--transition-fast);
}
.user-btn:hover { background: var(--bg-surface); border-color: var(--card-border); }
.user-name { font-size: 13px; font-weight: 500; color: var(--text-primary); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ════ Main Content ════ */
.main-content { flex: 1; overflow-y: auto; padding: 24px; }

/* ════ Notification Panel ════ */
.notify-panel { max-height: 360px; overflow-y: auto; }
.notify-hd { padding: 12px 16px; font-size: 14px; font-weight: 600; color: var(--text-primary); border-bottom: 1px solid var(--card-border); }
.notify-empty { padding: 32px 16px; text-align: center; font-size: 13px; color: var(--text-muted); }
.notify-item { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; cursor: pointer; transition: background var(--transition-fast); }
.notify-item:hover { background: var(--primary-light); }
.notify-sender { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px; }
.notify-content { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notify-time { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.notify-ft { padding: 12px 16px; text-align: center; font-size: 13px; color: var(--primary); font-weight: 500; cursor: pointer; border-top: 1px solid var(--card-border); }
.notify-ft:hover { background: var(--primary-light); }

/* ════ User Menu ════ */
.user-menu { padding: 4px 0; }
.user-menu-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; font-size: 13px; color: var(--text-primary); cursor: pointer; transition: all var(--transition-fast); }
.user-menu-item:hover { background: var(--primary-light); color: var(--primary); }
.user-menu-item.danger { color: var(--danger); }
.user-menu-item.danger:hover { background: var(--danger-light); }
.user-menu-divider { height: 1px; background: var(--card-border); margin: 4px 0; }

/* ════ Mobile Bottom Tabs ════ */
.mobile-tabs {
  display: none;
  height: 56px; flex-shrink: 0;
  background: rgba(255, 255, 255, 0.90);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border-top: 1px solid var(--card-border);
  align-items: center; justify-content: space-around;
  padding: 0 8px; padding-bottom: env(safe-area-inset-bottom, 0);
}
.tab-item {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 4px 12px; border: none; background: transparent;
  color: var(--text-muted); cursor: pointer;
  transition: all var(--transition-fast); min-width: 48px;
}
.tab-item.active { color: var(--primary); }
.tab-label { font-size: 10px; font-weight: 500; }

/* ════ Debug Panel ════ */
.debug-panel {
  position: fixed; bottom: 0; right: 0; width: 320px;
  background: #1C1917; color: #e0e0e0; z-index: 1000;
  border-radius: 8px 0 0 0; font-size: 12px;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.3);
  transition: max-height 0.2s; max-height: 300px; overflow: hidden;
}
.debug-panel.collapsed { max-height: 32px; }
.debug-header { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #333; font-weight: 600; font-size: 12px; }
.debug-header .el-button { color: #aaa; font-size: 11px; }
.debug-body { padding: 4px 10px 8px; max-height: 240px; overflow-y: auto; }
.debug-event { display: flex; gap: 8px; padding: 3px 0; border-bottom: 1px solid #2a2a3e; align-items: baseline; }
.debug-time { color: #666; flex-shrink: 0; font-size: 11px; }
.debug-msg { word-break: break-all; }
.debug-event.success .debug-msg { color: #57ab5a; }
.debug-event.error .debug-msg { color: #e5534b; }
.debug-event.api .debug-msg { color: #F59E0B; }
.debug-event.info .debug-msg { color: #8b949e; }
.debug-empty { color: #666; text-align: center; padding: 8px; }

/* ════ Responsive ════ */
@media (max-width: 768px) {
  .navbar-nav { display: none; }
  .navbar-inner { padding: 0 16px; }
  .user-name { display: none; }
  .mobile-tabs { display: flex; }
  .main-content { padding: 16px; padding-bottom: 72px; }
}
@media (min-width: 769px) {
  .mobile-tabs { display: none !important; }
}
</style>

<!-- ════ Unscoped Popover Styles ════ -->
<style>
.notify-popover, .user-popover {
  padding: 0 !important;
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--card-border) !important;
  box-shadow: var(--shadow-lg) !important;
}
</style>
