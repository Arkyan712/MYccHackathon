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
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">需求广场</h2>
        <p class="page-desc">发现校园中的求助、组队和技能交换需求，找到属于你的伙伴</p>
      </div>
      <el-button type="primary" class="header-create-btn" @click="router.push('/needs/new')">
        发布需求
      </el-button>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <span class="filter-label">类型筛选</span>
      <el-radio-group v-model="filterType" @change="onFilterChange">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="求助">求助</el-radio-button>
        <el-radio-button value="组队">组队</el-radio-button>
        <el-radio-button value="技能交换">技能交换</el-radio-button>
      </el-radio-group>
    </div>

    <!-- Content area -->
    <div v-loading="store.loading" class="plaza-content">
      <!-- Empty state -->
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
  max-width: 960px;
  margin: 0 auto;
  position: relative;
}

/* ---- Page header ---- */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  margin: 0 0 6px;
}

.page-desc {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.45);
  margin: 0;
}

.header-create-btn {
  height: 36px;
  font-size: 14px;
  border-radius: 6px;
  background: #0969da;
  border-color: #0969da;
  font-weight: 500;
  flex-shrink: 0;
}

.header-create-btn:hover {
  background: #0858b5;
  border-color: #0858b5;
}

/* ---- Filter bar ---- */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.filter-label {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.85);
  flex-shrink: 0;
}

.filter-bar :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
}

.filter-bar :deep(.el-radio-button__inner) {
  font-size: 13px;
  padding: 6px 16px;
}

.filter-bar :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-left-color: #d9d9d9;
}

/* ---- Card grid ---- */
.need-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.need-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.need-card :deep(.el-card__body) {
  padding: 20px;
}

.need-card:hover {
  border-color: #0969da;
  box-shadow: 0 2px 12px rgba(9, 105, 218, 0.08);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-status {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.45);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-author {
  font-size: 12px;
  color: #0969da;
  font-weight: 500;
}
.card-meta {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.35);
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
  background: #0969da;
  border-color: #0969da;
  box-shadow: 0 4px 14px rgba(9, 105, 218, 0.35);
  z-index: 100;
}

.fab-btn:hover {
  background: #0858b5;
  border-color: #0858b5;
  transform: scale(1.05);
}

.fab-btn:active {
  transform: scale(0.98);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .plaza-page {
    padding: 0 4px;
  }

  .need-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .page-header {
    flex-direction: column;
    gap: 12px;
  }

  .header-create-btn {
    width: 100%;
  }

  .fab-btn {
    right: 20px;
    bottom: 20px;
  }
}
</style>
