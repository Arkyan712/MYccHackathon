import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Welcome',
      component: () => import('@/views/WelcomeView.vue'),
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/plaza',
      name: 'Home',
      component: () => import('@/views/NeedPlazaView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/profile/setup',
      name: 'ProfileSetup',
      component: () => import('@/views/ProfileSetupView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/needs/new',
      name: 'NeedCreate',
      component: () => import('@/views/NeedCreateView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/needs/manage',
      name: 'NeedManage',
      component: () => import('@/views/NeedManageView.vue'),
      meta: { auth: true },
    },
    {
      path: '/needs/:id/matches',
      name: 'MatchResult',
      component: () => import('@/views/MatchResultView.vue'),
      meta: { auth: true },
    },
    {
      path: '/messages',
      name: 'Messages',
      component: () => import('@/views/MessagesView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/messages/:userId',
      name: 'MessagesWith',
      component: () => import('@/views/MessagesView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/agent',
      name: 'Agent',
      component: () => import('@/views/AgentView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/agent/:sessionId',
      name: 'AgentSession',
      component: () => import('@/views/AgentView.vue'),
      meta: { auth: true, mobileLayout: true },
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { auth: true },
    },
  ],
})

router.beforeEach((to, _from) => {
  const auth = useAuthStore()

  if (to.meta.auth && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.meta.guest && auth.isLoggedIn) {
    return '/plaza'
  }
  if (to.path === '/' && auth.isLoggedIn) {
    return '/plaza'
  }
})

export default router
