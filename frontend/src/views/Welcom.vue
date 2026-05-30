<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import bgImage from '@/assets/home.jpg'

const router = useRouter()
const particles = ref<Array<{ x: number; y: number; size: number; duration: number; delay: number }>>([])
const statsAnimated = ref({ users: 0, matches: 0, rate: 0 })

function goLogin() {
  router.push('/login')
}

function goRegister() {
  router.push('/login?tab=register')
}

function scrollToFeatures() {
  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
}

function animateStats() {
  const targets = { users: 1234, matches: 5678, rate: 98 }
  const duration = 1500
  const start = performance.now()
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)
    statsAnimated.value.users = Math.round(targets.users * ease)
    statsAnimated.value.matches = Math.round(targets.matches * ease)
    statsAnimated.value.rate = Math.round(targets.rate * ease)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

onMounted(() => {
  for (let i = 0; i < 30; i++) {
    particles.value.push({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 4 + 2,
      duration: Math.random() * 20 + 15,
      delay: Math.random() * 10
    })
  }
  // Start counting when stats section is visible
  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      animateStats()
      observer.disconnect()
    }
  })
  const el = document.getElementById('hero-stats')
  if (el) observer.observe(el)
})
</script>

<template>
  <div class="welcome-page">
    <div class="welcome-bg" :style="{ backgroundImage: `url(${bgImage})` }">
      <div class="bg-overlay" />
      <div class="floating-particles">
        <span
          v-for="(p, i) in particles"
          :key="i"
          class="particle"
          :style="{
            left: p.x + '%',
            top: p.y + '%',
            width: p.size + 'px',
            height: p.size + 'px',
            animationDuration: p.duration + 's',
            animationDelay: p.delay + 's'
          }"
        />
      </div>
    </div>

    <header class="welcome-header">
      <div class="header-content">
        <div class="logo-area">
          <span class="logo-icon">🎓</span>
          <span class="logo-text">AI Campus</span>
        </div>
        <nav class="header-nav">
          <span class="nav-hint">已有账号？</span>
          <el-button text class="nav-login-btn" @click="goLogin">
            登录
            <span class="arrow">→</span>
          </el-button>
        </nav>
      </div>
    </header>

    <main class="welcome-main">
      <div class="hero-section">
        <div class="hero-badge">
          <span class="badge-dot" />
          <span>校园专属 · AI 智能匹配</span>
        </div>

        <h1 class="hero-title">
          找到你的
          <span class="title-highlight">校园伙伴</span>
        </h1>

        <p class="hero-subtitle">
          通过 AI 语义理解与智能匹配，帮你找到最合适的队友。<br />
          无论是课程求助、项目组队还是技能交换，这里都能精准连接。
        </p>

        <div class="hero-cta">
          <el-button class="btn-primary" size="large" @click="goRegister">
            <span class="btn-icon">✨</span>
            开始探索
          </el-button>
          <el-button class="btn-secondary" size="large" @click="goLogin">
            我已有账号
          </el-button>
        </div>

        <div id="hero-stats" class="hero-stats">
          <div class="stat-item">
            <span class="stat-number">{{ statsAnimated.users.toLocaleString() }}+</span>
            <span class="stat-label">校园用户</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-number">{{ statsAnimated.matches.toLocaleString() }}</span>
            <span class="stat-label">成功匹配</span>
          </div>
          <div class="stat-divider" />
          <div class="stat-item">
            <span class="stat-number">{{ statsAnimated.rate }}%</span>
            <span class="stat-label">满意度</span>
          </div>
        </div>

        <div class="scroll-hint" @click="scrollToFeatures">
          <span class="scroll-text">了解更多</span>
          <span class="scroll-chevron">↓</span>
        </div>
      </div>

      <div id="features" class="features-section">
        <h2 class="section-title">为什么选择我们</h2>

        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon-wrap">
              <span class="feature-icon">🎯</span>
            </div>
            <h3 class="feature-title">精准智能匹配</h3>
            <p class="feature-desc">基于 DeepSeek + Qwen3 大模型，理解语义、匹配技能、预测默契度</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon-wrap">
              <span class="feature-icon">🤝</span>
            </div>
            <h3 class="feature-title">发现志同道合</h3>
            <p class="feature-desc">不只是找队友，更是找到真正与你互补、能够共同成长的人</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon-wrap">
              <span class="feature-icon">💡</span>
            </div>
            <h3 class="feature-title">技能互补成长</h3>
            <p class="feature-desc">擅长前端的你，缺少后端伙伴？来这里精准找到技能互补的同学</p>
          </div>

          <div class="feature-card">
            <div class="feature-icon-wrap">
              <span class="feature-icon">🔒</span>
            </div>
            <h3 class="feature-title">隐私安全保护</h3>
            <p class="feature-desc">端到端加密传输，你的个人信息只用于匹配，绝不泄露</p>
          </div>
        </div>
      </div>

      <div class="how-it-works">
        <h2 class="section-title">如何使用</h2>

        <div class="steps">
          <div class="step-item">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4>完善个人资料</h4>
              <p>填写你的技能标签和需求描述</p>
            </div>
          </div>

          <div class="step-arrow">→</div>

          <div class="step-item">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4>发布或浏览需求</h4>
              <p>发布你的求助/组队需求</p>
            </div>
          </div>

          <div class="step-arrow">→</div>

          <div class="step-item">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4>AI 智能匹配</h4>
              <p>等待 AI 为你推荐最合适的人选</p>
            </div>
          </div>

          <div class="step-arrow">→</div>

          <div class="step-item">
            <div class="step-number">4</div>
            <div class="step-content">
              <h4>开始合作</h4>
              <p>联系心仪的伙伴，开始你们的项目</p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <footer class="welcome-footer">
      <div class="footer-content">
        <div class="footer-brand">
          <span class="footer-logo">🎓 AI Campus</span>
          <p class="footer-tagline">校园AI互助匹配平台 · 绵阳市安州区</p>
        </div>

        <div class="footer-links">
          <a href="javascript:void(0)" class="footer-link">关于我们</a>
          <span class="link-divider">·</span>
          <a href="javascript:void(0)" class="footer-link">使用指南</a>
          <span class="link-divider">·</span>
          <a href="javascript:void(0)" class="footer-link">联系我们</a>
        </div>

        <div class="footer-bottom">
          <div class="security-badge">
            <svg class="shield-icon" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L4 5V11.09C4 16.14 7.41 20.85 12 22C16.59 20.85 20 16.14 20 11.09V5L12 2ZM12 4.18L18 6.5V11.09C18 15.09 15.45 18.79 12 19.92C8.55 18.79 6 15.09 6 11.09V6.5L12 4.18Z" fill="currentColor"/>
            </svg>
            <span>SSL 安全加密</span>
          </div>
          <p class="copyright">© 2026 AI Campus. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.welcome-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-x: hidden;
}

.welcome-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.bg-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 30%, rgba(99, 102, 241, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse 60% 40% at 80% 70%, rgba(168, 85, 247, 0.1) 0%, transparent 50%),
    linear-gradient(135deg, rgba(30, 58, 95, 0.3) 0%, rgba(45, 74, 111, 0.25) 50%, rgba(30, 58, 95, 0.3) 100%);
}

.floating-particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  animation: float-particle linear infinite;
}

@keyframes float-particle {
  0% {
    transform: translateY(100vh) rotate(0deg);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) rotate(720deg);
    opacity: 0;
  }
}

.welcome-header {
  position: relative;
  z-index: 100;
  padding: 0 48px;
  height: 80px;
  display: flex;
  align-items: center;
}

.header-content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  color: #ffffff;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
  letter-spacing: 0.5px;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-hint {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.85);
}

.nav-login-btn {
  color: #ffffff !important;
  font-weight: 600;
  font-size: 15px;
  padding: 10px 24px !important;
  border-radius: 24px !important;
  background: rgba(255, 255, 255, 0.15) !important;
  border: 1.5px solid rgba(255, 255, 255, 0.35) !important;
  transition: all 0.3s ease;
}

.nav-login-btn:hover {
  background: rgba(255, 255, 255, 0.25) !important;
  border-color: rgba(255, 255, 255, 0.6) !important;
  transform: translateY(-2px);
}

.nav-login-btn .arrow {
  margin-left: 6px;
  transition: transform 0.3s;
}

.nav-login-btn:hover .arrow {
  transform: translateX(4px);
}

.welcome-main {
  flex: 1;
  position: relative;
  z-index: 10;
  padding: 40px 24px 60px;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}

.hero-section {
  text-align: center;
  padding: 60px 0 80px;
  animation: fadeInUp 0.8s ease forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(40px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 28px;
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.2); }
}

.hero-title {
  font-size: 52px;
  font-weight: 800;
  color: #fff8f0;
  margin: 0 0 20px;
  line-height: 1.2;
  text-shadow: 0 4px 20px rgba(139, 69, 19, 0.5), 0 2px 8px rgba(0, 0, 0, 0.3);
}

.title-highlight {
  background: linear-gradient(135deg, #ffd700 0%, #ffb347 50%, #ff8c69 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 18px;
  color: rgba(255, 250, 240, 0.95);
  line-height: 1.8;
  margin: 0 auto 40px;
  max-width: 560px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.hero-cta {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 48px;
}

.btn-primary {
  height: 56px;
  padding: 0 36px !important;
  font-size: 17px !important;
  font-weight: 600 !important;
  border-radius: 28px !important;
  background: linear-gradient(135deg, #ff8c69 0%, #ff7b54 100%) !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 8px 24px rgba(255, 140, 105, 0.4);
  transition: all 0.3s ease;
}

.btn-primary:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(255, 140, 105, 0.5);
}

.btn-primary .btn-icon {
  margin-right: 8px;
  font-size: 18px;
}

.btn-secondary {
  height: 56px;
  padding: 0 32px !important;
  font-size: 16px !important;
  font-weight: 500 !important;
  border-radius: 28px !important;
  background: rgba(255, 255, 255, 0.1) !important;
  border: 1.5px solid rgba(255, 255, 255, 0.35) !important;
  color: #ffffff !important;
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.55) !important;
  transform: translateY(-2px);
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;
  padding: 24px 40px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(16px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  max-width: 480px;
  margin: 0 auto;
}

.scroll-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-top: 36px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.3s;
  user-select: none;
}

.scroll-hint:hover {
  opacity: 1;
}

.scroll-text {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.scroll-chevron {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.8);
  animation: bounce-down 1.5s ease-in-out infinite;
}

@keyframes bounce-down {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(8px); }
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-number {
  font-size: 28px;
  font-weight: 800;
  color: #ffffff;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.stat-divider {
  width: 1px;
  height: 36px;
  background: rgba(255, 255, 255, 0.2);
}

.features-section {
  padding: 60px 0 80px;
  animation: fadeInUp 0.8s ease 0.2s forwards;
  opacity: 0;
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  text-align: center;
  margin: 0 0 48px;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 28px 24px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  position: relative;
  overflow: hidden;
}

.feature-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 20px;
  opacity: 0;
  background: radial-gradient(circle at center, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
  transition: opacity 0.35s ease;
}

.feature-card:hover::before {
  opacity: 1;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.16);
  transform: translateY(-8px);
  border-color: rgba(255, 255, 255, 0.35);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}

.feature-icon-wrap {
  width: 64px;
  height: 64px;
  background: rgba(143, 188, 212, 0.25);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  transition: transform 0.3s ease, background 0.3s ease;
}

.feature-card:hover .feature-icon-wrap {
  transform: scale(1.08);
  background: rgba(143, 188, 212, 0.35);
}

.feature-icon {
  font-size: 32px;
}

.feature-title {
  font-size: 17px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 10px;
}

.feature-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  margin: 0;
}

.how-it-works {
  padding: 60px 0 80px;
  animation: fadeInUp 0.8s ease 0.4s forwards;
  opacity: 0;
}

.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 14px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  padding: 16px 20px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.step-number {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #8fbcd4 0%, #7aaccc 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #ffffff;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px;
}

.step-content p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  margin: 0;
}

.step-arrow {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.4);
}

.welcome-footer {
  position: relative;
  z-index: 10;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: 40px 24px;
}

.footer-content {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.footer-brand {
  text-align: center;
}

.footer-logo {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
}

.footer-tagline {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin: 6px 0 0;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-link {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-link:hover {
  color: #ffffff;
}

.link-divider {
  color: rgba(255, 255, 255, 0.4);
}

.footer-bottom {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  width: 100%;
}

.security-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.shield-icon {
  width: 14px;
  height: 14px;
}

.copyright {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0;
}

@media (max-width: 900px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-title {
    font-size: 40px;
  }

  .steps {
    flex-direction: column;
    gap: 16px;
  }

  .step-arrow {
    transform: rotate(90deg);
  }
}

@media (max-width: 600px) {
  .welcome-header {
    padding: 0 20px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 32px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .hero-cta {
    flex-direction: column;
    align-items: center;
  }

  .hero-stats {
    flex-direction: column;
    gap: 20px;
  }

  .stat-divider {
    width: 60px;
    height: 1px;
  }

  .section-title {
    font-size: 24px;
  }
}
</style>
