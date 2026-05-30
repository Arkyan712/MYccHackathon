<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNeedsStore } from '@/stores/needs'
import type { Need } from '@/types'
import { Plus } from '@element-plus/icons-vue'

const router = useRouter()
const store = useNeedsStore()

const filterType = ref('')
const page = ref(1)
const pageSize = 20

const totalPages = computed(() => Math.ceil(store.total / pageSize))

onMounted(() => load())

async function load() {
  const params: { page?: number; page_size?: number; type?: string } = {
    page: page.value,
    page_size: pageSize,
  }
  if (filterType.value) {
    params.type = filterType.value
  }
  await store.fetchNeeds(params)
}

function onFilterChange(val: string) {
  filterType.value = val
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function goToMatch(needId: number) {
  router.push(`/needs/${needId}/matches`)
}

function typeTagType(type: Need['type']) {
  switch (type) {
    case '求助': return 'danger'
    case '组队': return 'success'
    case '技能交换': return 'warning'
    default: return 'info'
  }
}

function formatDate(iso: string) {
  return iso.slice(0, 10)
}
</script>

<template>
  <div class="plaza-page">
    <!-- Banner -->
    <div class="plaza-banner">
      <div class="banner-text">
        <h1>发现你的校园伙伴</h1>
        <p>浏览求助、组队和技能交换需求，AI 帮你找到最匹配的人</p>
      </div>
      <div class="banner-action">
        <el-button type="primary" @click="router.push('/needs/new')">+ 发布需求</el-button>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <span class="filter-label">分类：</span>
      <button
        v-for="opt in [{v:'',l:'全部'},{v:'求助',l:'🔍 求助'},{v:'组队',l:'👥 组队'},{v:'技能交换',l:'🤝 技能交换'}]"
        :key="opt.v"
        class="filter-pill"
        :class="{ active: filterType === opt.v }"
        @click="onFilterChange(opt.v)"
      >{{ opt.l }}</button>
    </div>

    <!-- Content area -->
    <div v-loading="store.loading" class="plaza-content">
      <el-empty
        v-if="!store.loading && store.needs.length === 0"
        description="还没有需求，快去发布第一个吧"
      />

      <!-- Card grid -->
      <div v-else class="need-grid">
        <el-card
          v-for="need in store.needs"
          :key="need.id"
          shadow="never"
          class="need-card"
          :class="{
            'type-help': need.type === '求助',
            'type-team': need.type === '组队',
            'type-swap': need.type === '技能交换'
          }"
          @click="goToMatch(need.id)"
        >
          <div class="card-body">
            <div class="card-top">
              <el-tag :type="typeTagType(need.type)" size="small" effect="plain">
                {{ need.type }}
              </el-tag>
              <span class="card-status">{{ need.status }}</span>
            </div>
            <h3 class="card-title">{{ need.title }}</h3>
            <p class="card-desc">{{ need.description }}</p>
            <div class="card-footer">
              <span class="card-author">{{ need.username }}</span>
              <span class="card-meta">{{ formatDate(need.created_at) }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="plaza-pagination">
        <el-pagination
          v-model:current-page="page"
          :total="store.total"
          :page-size="pageSize"
          background
          layout="prev, pager, next"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- Floating action button -->
    <el-tooltip content="发布需求" placement="left">
      <el-button
        type="primary"
        circle
        size="large"
        class="fab-btn"
        @click="router.push('/needs/new')"
      >
        <el-icon :size="22"><Plus /></el-icon>
      </el-button>
    </el-tooltip>
  </div>
</template>

<style scoped>
.plaza-page {
  max-width: 1000px;
  margin: 0 auto;
  position: relative;
  padding: 8px 0;
}

/* ---- Banner ---- */
.plaza-banner {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(126, 172, 204, 0.12) 0%, rgba(126, 172, 204, 0.06) 50%, rgba(126, 172, 204, 0.1) 100%);
  border: 1px solid rgba(126, 172, 204, 0.15);
  border-radius: var(--radius-xl);
  padding: 32px 36px;
  margin-bottom: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
}
.plaza-banner::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 400px;
  height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(126, 172, 204, 0.15) 0%, transparent 70%);
  animation: banner-float 8s ease-in-out infinite;
}
@keyframes banner-float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 20px); }
}
.banner-text {
  position: relative;
  z-index: 1;
}
.banner-text h1 {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--text-primary), var(--primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 6px;
}
.banner-text p {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}
.banner-action {
  position: relative;
  z-index: 1;
}
.banner-action .el-button {
  background: var(--primary-gradient) !important;
  border: none !important;
  font-weight: 700 !important;
  height: 44px;
  padding: 0 28px !important;
  border-radius: var(--radius-full) !important;
  box-shadow: 0 6px 18px rgba(126, 172, 204, 0.35) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.banner-action .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(126, 172, 204, 0.45) !important;
}

/* ---- Filter bar ---- */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
  font-weight: 600;
}
.filter-pill {
  position: relative;
  overflow: hidden;
  padding: 8px 20px;
  border-radius: var(--radius-full);
  border: 1px solid var(--card-border);
  background: #fff;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.filter-pill::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--primary-gradient);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.filter-pill:hover::before {
  opacity: 0.08;
}
.filter-pill:hover {
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-1px);
}
.filter-pill.active {
  background: var(--primary-gradient);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 14px rgba(126, 172, 204, 0.35);
}
.filter-pill.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 2px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 1px;
}

/* ---- Card grid ---- */
.need-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.need-card {
  border: 1px solid var(--card-border) !important;
  border-radius: var(--radius-lg) !important;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: var(--card-shadow) !important;
  overflow: hidden;
  position: relative;
  background: #fff !important;
}

.need-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  transition: all 0.3s ease;
}
.need-card.type-help::before { background: linear-gradient(180deg, #EF4444, #F87171); }
.need-card.type-team::before { background: linear-gradient(180deg, var(--primary), var(--primary-hover)); }
.need-card.type-swap::before { background: linear-gradient(180deg, var(--accent), var(--accent-hover)); }

.need-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  opacity: 0;
  transition: opacity 0.3s ease;
  background: linear-gradient(135deg, rgba(126, 172, 204, 0.08) 0%, rgba(126, 172, 204, 0.04) 100%);
  pointer-events: none;
}

.need-card:hover::after {
  opacity: 1;
}

.need-card :deep(.el-card__body) {
  padding: 22px 22px 22px 26px;
}

.need-card:hover {
  border-color: rgba(126, 172, 204, 0.3) !important;
  box-shadow: var(--card-shadow-hover) !important;
  transform: translateY(-8px) scale(1.02);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-status {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
  padding: 2px 8px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s ease;
}
.need-card:hover .card-title {
  color: var(--primary);
}

.card-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: opacity 0.3s ease;
}
.need-card:hover .card-desc {
  opacity: 0.9;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--bg-surface);
}

.card-author {
  font-size: 13px;
  color: var(--primary);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}
.card-author::before {
  content: '👤';
  font-size: 12px;
}
.card-meta {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}
.card-meta::before {
  content: '📅';
  font-size: 11px;
}

/* ---- Pagination ---- */
.plaza-pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-bottom: 24px;
}

/* ---- Floating action button ---- */
.fab-btn {
  position: fixed;
  right: 40px;
  bottom: 40px;
  width: 52px;
  height: 52px;
  background: var(--primary-gradient) !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(126, 172, 204, 0.35) !important;
  z-index: 100;
}
.fab-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(126, 172, 204, 0.45) !important;
}
.fab-btn:active { transform: scale(0.96); }

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .plaza-banner { flex-direction: column; text-align: center; padding: 24px 20px; }
  .need-grid { grid-template-columns: 1fr; gap: 12px; }
  .fab-btn { right: 20px; bottom: 20px; }
}
</style>
