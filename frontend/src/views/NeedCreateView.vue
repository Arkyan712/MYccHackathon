<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNeedsStore } from '@/stores/needs'
import { ElMessage } from 'element-plus'
import { MagicStick, EditPen, Refresh } from '@element-plus/icons-vue'
import * as needsApi from '@/api/needs'

const router = useRouter()
const store = useNeedsStore()
const loading = ref(false)
const generating = ref(false)
const polishing = ref(false)
const showPreview = ref(false)
const previewText = ref('')
const previewMode = ref<'polish' | 'generate'>('polish')
const form = reactive({ type: '组队', title: '', description: '', selection_mode: 'single' as 'single' | 'multi' })

const hasTitle = computed(() => form.title.trim().length > 0)
const hasDescription = computed(() => form.description.trim().length > 0)

const typeOptions = [
  { value: '求助', label: '求助', icon: '🔍', desc: '寻求帮助' },
  { value: '组队', label: '组队', icon: '👥', desc: '组建团队' },
  { value: '技能交换', label: '技能交换', icon: '🤝', desc: '技能互换' },
]

const needTemplates = [
  { type: '组队', title: '寻找黑客松项目队友', description: '我正在准备一个校园创新项目，希望找到对前端、后端或产品设计感兴趣的同学一起组队。项目目标是做出可演示的 MVP，欢迎有 Vue、Python、UI 设计、路演表达经验的同学联系。', selection_mode: 'multi' as const },
  { type: '求助', title: '课程作业/项目技术求助', description: '我在课程项目中遇到技术问题，希望找一位熟悉相关方向的同学一起梳理思路。希望对方能帮我定位问题、讲清楚关键知识点，并给出可执行的改进建议。', selection_mode: 'single' as const },
  { type: '技能交换', title: '技能互助学习搭子', description: '我希望和同学进行技能交换：我可以分享自己擅长的内容，也想学习对方熟悉的方向。适合每周约定一次交流，互相给反馈、一起推进小作品。', selection_mode: 'multi' as const },
]

const templateOptions = computed(() => needTemplates.filter(t => t.type === form.type))

function applyTemplate(tpl: typeof needTemplates[number]) {
  form.title = tpl.title; form.description = tpl.description; form.selection_mode = tpl.selection_mode
  ElMessage.success('已套用需求模板')
}

async function handleGenerate() {
  if (!hasTitle.value) { ElMessage.warning('请先填写标题'); return }
  generating.value = true
  try {
    const { data } = await needsApi.generateDescription({ need_type: form.type, title: form.title })
    previewText.value = data.result; previewMode.value = 'generate'; showPreview.value = true
  } catch (e: any) {
    ElMessage.error('生成失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally { generating.value = false }
}

async function handlePolish() {
  if (!hasTitle.value || !hasDescription.value) { ElMessage.warning('请先填写标题和描述'); return }
  polishing.value = true
  try {
    const { data } = await needsApi.polishDescription({ need_type: form.type, title: form.title, description: form.description })
    previewText.value = data.result; previewMode.value = 'polish'; showPreview.value = true
  } catch (e: any) {
    ElMessage.error('润色失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally { polishing.value = false }
}

function acceptPreview() { form.description = previewText.value; showPreview.value = false; ElMessage.success('已填入描述') }

function retryWithFeedback(direction: 'more' | 'rewrite') {
  if (direction === 'more') {
    if (previewMode.value === 'polish') { form.description = previewText.value; showPreview.value = false; setTimeout(() => handlePolish(), 100) }
    else { showPreview.value = false; setTimeout(() => handleGenerate(), 100) }
  } else { showPreview.value = false }
}

function rejectPreview() { showPreview.value = false; ElMessage.info('已取消，可以修改后重新润色') }

async function submit() {
  if (!form.title.trim() || !form.description.trim()) { ElMessage.warning('请填写标题和描述'); return }
  loading.value = true
  try {
    const need = await store.createNeed({ type: form.type, title: form.title.trim(), description: form.description.trim(), selection_mode: form.selection_mode })
    ElMessage.success('发布成功，正在跳转到匹配进度...')
    router.push(`/needs/${need.id}/matches`)
  } catch { ElMessage.error('发布失败') } finally { loading.value = false }
}
</script>

<template>
  <div class="create-page">
    <div class="page-header">
      <h2>发布需求</h2>
      <p>描述你的需求，AI 帮你精准匹配最合适的伙伴</p>
    </div>

    <div class="create-layout">
      <!-- Left: Form -->
      <div class="create-main">
        <el-card shadow="never" class="page-card">
          <el-form label-position="top" class="create-form">
            <el-form-item label="需求类型">
              <div class="type-selector">
                <div v-for="t in typeOptions" :key="t.value" class="type-card" :class="{ selected: form.type === t.value }" @click="form.type = t.value">
                  <span class="type-icon">{{ t.icon }}</span>
                  <span class="type-label">{{ t.label }}</span>
                  <span class="type-desc">{{ t.desc }}</span>
                </div>
              </div>
            </el-form-item>

            <el-form-item label="匹配方式">
              <el-radio-group v-model="form.selection_mode">
                <el-radio value="single">单选（从匹配结果中选1人）</el-radio>
                <el-radio value="multi">多选（可选择多人合作）</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="标题">
              <el-input v-model="form.title" placeholder="简短概括你的需求，例如：找一名前端队友参加黑客松" maxlength="60" show-word-limit />
            </el-form-item>

            <el-form-item label="详细描述">
              <el-input v-model="form.description" type="textarea" :rows="5" placeholder="详细描述你的需求，AI 会自动分析关键词并匹配最合适的人选..." maxlength="500" show-word-limit />
            </el-form-item>

            <div v-if="showPreview" class="preview-panel">
              <div class="preview-header"><span class="preview-label">{{ previewMode === 'generate' ? 'AI 生成' : 'AI 润色' }}结果</span></div>
              <div class="preview-body">{{ previewText }}</div>
              <div class="preview-actions">
                <el-button size="small" @click="rejectPreview">取消</el-button>
                <el-button size="small" @click="retryWithFeedback('more')" :loading="polishing || generating"><el-icon :size="13"><Refresh /></el-icon> 再来一次</el-button>
                <el-button size="small" @click="retryWithFeedback('rewrite')"><el-icon :size="13"><EditPen /></el-icon> 修改后重试</el-button>
                <el-button size="small" type="primary" @click="acceptPreview">满意，填入</el-button>
              </div>
            </div>

            <el-button type="primary" :loading="loading" @click="submit" size="large" class="submit-btn">
              {{ loading ? 'AI 分析中...' : '🚀 发布并启动 AI 匹配' }}
            </el-button>
          </el-form>
        </el-card>
      </div>

      <!-- Right: AI Tools -->
      <div class="create-sidebar">
        <el-card shadow="never" class="side-card">
          <template #header><span class="side-title">📋 需求模板库</span></template>
          <div class="template-list">
            <button v-for="tpl in templateOptions" :key="tpl.title" type="button" class="template-item" @click="applyTemplate(tpl)">
              <span class="template-title">{{ tpl.title }}</span>
              <span class="template-desc">{{ tpl.description.slice(0, 40) }}...</span>
            </button>
          </div>
        </el-card>

        <el-card shadow="never" class="side-card">
          <template #header><span class="side-title">🤖 AI 写作助手</span></template>
          <p class="ai-hint">AI 根据标题自动生成完整描述，参考你的历史风格。</p>
          <el-button :disabled="!hasTitle" :loading="generating" @click="handleGenerate" class="ai-generate-btn" type="warning" plain>
            <el-icon :size="15"><MagicStick /></el-icon>
            {{ generating ? '生成中...' : 'AI 生成描述' }}
          </el-button>
          <el-divider />
          <p class="ai-hint">写好后让 AI 帮你润色优化，表达更清晰。</p>
          <el-button :disabled="!hasTitle || !hasDescription" :loading="polishing" @click="handlePolish" class="ai-polish-btn" type="primary" plain>
            <el-icon :size="14"><EditPen /></el-icon>
            AI 润色优化
          </el-button>
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-page { max-width: 1000px; margin: 0 auto; padding: 8px 0; }
.page-header { margin-bottom: 24px; }
.page-header h2 { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px; }
.page-header p { font-size: 14px; color: var(--text-secondary); margin: 0; }

/* -- Two-column layout -- */
.create-layout { display: grid; grid-template-columns: 1fr 280px; gap: 24px; align-items: start; }
.create-sidebar { position: sticky; top: 80px; display: flex; flex-direction: column; gap: 16px; }

.page-card, .side-card { border: 1px solid var(--card-border) !important; border-radius: var(--radius-lg) !important; box-shadow: var(--card-shadow) !important; }
.side-title { font-size: 14px; font-weight: 700; }

/* -- Type selector -- */
.type-selector { display: flex; gap: 14px; width: 100%; }
.type-card { 
  flex: 1; 
  padding: 20px 12px; 
  text-align: center; 
  border: 2px solid var(--card-border); 
  border-radius: var(--radius-lg); 
  cursor: pointer; 
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  gap: 8px; 
  background: #fff;
  position: relative;
  overflow: hidden;
}
.type-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--primary-gradient);
  opacity: 0;
  transition: opacity 0.3s ease;
}
.type-card:hover::before {
  opacity: 0.05;
}
.type-card:hover { 
  border-color: var(--primary); 
  transform: translateY(-4px);
}
.type-card.selected { 
  border-color: var(--primary); 
  background: linear-gradient(135deg, rgba(126, 172, 204, 0.1) 0%, rgba(126, 172, 204, 0.05) 100%); 
  box-shadow: var(--shadow-glow-blue);
}
.type-card.selected::after {
  content: '✓';
  position: absolute;
  top: 10px;
  right: 10px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
}
.type-icon { font-size: 34px; transition: transform 0.3s ease; }
.type-card:hover .type-icon { transform: scale(1.1) rotate(5deg); }
.type-label { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.type-desc { font-size: 12px; color: var(--text-secondary); }

/* -- Templates -- */
.template-list { display: flex; flex-direction: column; gap: 8px; }
.template-item { 
  border: 1px solid var(--card-border); 
  border-radius: var(--radius-md); 
  background: #fff; 
  padding: 12px 14px; 
  text-align: left; 
  cursor: pointer; 
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
  width: 100%;
  position: relative;
  overflow: hidden;
}
.template-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent);
  transform: scaleY(0);
  transition: transform 0.3s ease;
}
.template-item:hover { 
  border-color: var(--accent); 
  background: var(--accent-light);
  transform: translateX(4px);
}
.template-item:hover::before {
  transform: scaleY(1);
}
.template-title { display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); }
.template-desc { display: block; margin-top: 4px; font-size: 12px; color: var(--text-secondary); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* -- AI tools -- */
.ai-hint { font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin: 0 0 12px; }
.ai-generate-btn, .ai-polish-btn { width: 100%; }
.ai-generate-btn { 
  background: var(--accent-gradient) !important; 
  color: var(--text-inverse) !important; 
  border: none !important; 
  font-weight: 600 !important;
  box-shadow: 0 4px 12px rgba(109, 179, 212, 0.3) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.ai-generate-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(109, 179, 212, 0.4) !important;
}
.ai-polish-btn {
  box-shadow: 0 4px 12px rgba(126, 172, 204, 0.25) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.ai-polish-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(126, 172, 204, 0.35) !important;
}

/* -- Preview -- */
.preview-panel { 
  margin-top: 16px; 
  border: 1px solid var(--accent); 
  border-radius: var(--radius-lg); 
  overflow: hidden; 
  background: linear-gradient(135deg, rgba(109, 179, 212, 0.08) 0%, rgba(109, 179, 212, 0.04) 100%);
}
.preview-header { 
  padding: 12px 16px; 
  border-bottom: 1px solid rgba(109, 179, 212, 0.2); 
  background: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
}
.preview-header::before {
  content: '🤖';
  animation: preview-bounce 2s ease-in-out infinite;
}
@keyframes preview-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}
.preview-label { font-size: 14px; font-weight: 700; color: var(--accent-hover); }
.preview-body { 
  padding: 16px; 
  font-size: 14px; 
  line-height: 1.8; 
  color: var(--text-primary); 
  white-space: pre-wrap; 
  min-height: 80px;
  position: relative;
}
.preview-body::after {
  content: '|';
  animation: cursor-blink 1s step-end infinite;
  color: var(--accent);
  font-weight: bold;
}
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.preview-actions { 
  display: flex; 
  gap: 8px; 
  padding: 12px 16px; 
  border-top: 1px solid rgba(109, 179, 212, 0.2); 
  background: #fff; 
  justify-content: flex-end; 
  flex-wrap: wrap; 
}

/* -- Submit -- */
.submit-btn { width: 100% !important; margin-top: 8px !important; font-size: 15px !important; height: 46px !important; border-radius: var(--radius-md) !important; }

@media (max-width: 768px) {
  .create-layout { grid-template-columns: 1fr; }
  .type-selector { flex-direction: column; }
}
</style>
