<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  BarChart3,
  BookOpen,
  Bot,
  Building2,
  Calculator,
  Menu,
  ScanEye,
  Sparkles,
  X,
  FlaskConical,
} from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import LogoMark from './LogoMark.vue'
import ToastStack from './ToastStack.vue'

const route = useRoute()
const app = useAppStore()
const mobileOpen = ref(false)

const navItems = [
  { to: '/', label: '数据驾驶舱', short: '市场全景', icon: BarChart3, index: '01' },
  { to: '/valuation', label: '智能估值', short: '价格与解释', icon: Building2, index: '02' },
  { to: '/investment', label: '投资决策', short: '现金流与回报', icon: Calculator, index: '03' },
  { to: '/agent', label: 'AI 顾问', short: '多工具 Agent', icon: Bot, index: '04' },
  { to: '/knowledge', label: '知识库', short: 'RAG 与引用', icon: BookOpen, index: '05' },
  { to: '/vision', label: '图像分析', short: '多模态观察', icon: ScanEye, index: '06' },
  { to: '/research', label: '研究实验室', short: '模型与数据', icon: FlaskConical, index: '07' },
]

const pageTitle = computed(() => String(route.meta.title ?? 'HouseMind AI'))
const pageEyebrow = computed(() => String(route.meta.eyebrow ?? 'PROPERTY INTELLIGENCE'))
const modeLabel = computed(() => app.meta?.mode.llm_label ?? (app.loading ? '连接中' : '本地模式'))
const modeTone = computed(() => (app.meta?.mode.llm === 'deepseek' ? 'live' : 'local'))

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
  },
)

onMounted(() => app.load())
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'is-open': mobileOpen }">
      <div class="brand">
        <LogoMark :size="38" />
        <div class="brand-copy">
          <div class="brand-name">HOUSEMIND <span>AI</span></div>
          <div class="brand-sub">PROPERTY INTELLIGENCE</div>
        </div>
        <button class="icon-btn sidebar-close" aria-label="关闭菜单" @click="mobileOpen = false">
          <X :size="18" />
        </button>
      </div>

      <div class="sidebar-section-label">WORKSPACE</div>
      <nav class="nav-list" aria-label="主导航">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item">
          <span class="nav-index">{{ item.index }}</span>
          <component :is="item.icon" :size="17" :stroke-width="1.6" class="nav-icon" />
          <span class="nav-copy">
            <span class="nav-label">{{ item.label }}</span>
            <span class="nav-short">{{ item.short }}</span>
          </span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <div class="model-status">
          <span class="status-orbit"><span class="status-dot" /></span>
          <div>
            <div class="model-title">XGBOOST · LIVE</div>
            <div class="model-meta">MAE $59.5K · R² 0.916</div>
          </div>
        </div>
        <div class="sidebar-divider" />
        <div class="sidebar-note">
          <Sparkles :size="14" />
          <span>数据截止 2015-05<br />仅适用于 King County</span>
        </div>
        <div class="sidebar-legal">HOUSEMIND AI © 2026<br />BUILT FOR DECISIONS, NOT GUESSES.</div>
      </div>
    </aside>

    <div v-if="mobileOpen" class="sidebar-scrim" @click="mobileOpen = false" />

    <div class="workspace">
      <header class="topbar">
        <button class="icon-btn mobile-menu" aria-label="打开菜单" @click="mobileOpen = true">
          <Menu :size="20" />
        </button>
        <div class="topbar-context">
          <div class="topbar-eyebrow">{{ pageEyebrow }} <span>/</span> {{ route.meta.index }}</div>
          <div class="topbar-title">{{ pageTitle }}</div>
        </div>
        <div class="topbar-actions">
          <div class="mode-pill" :class="modeTone">
            <span class="mode-dot" />
            <span>{{ modeLabel }}</span>
          </div>
          <div class="topbar-period">
            <span class="topbar-period-label">SAMPLE</span>
            <span>2014.05 — 2015.05</span>
          </div>
          <RouterLink to="/valuation" class="btn btn-primary topbar-cta">
            <Building2 :size="15" />
            开始估值
          </RouterLink>
        </div>
      </header>

      <main class="page-wrap">
        <div v-if="app.error" class="service-banner" role="alert">
          <span class="service-banner-dot" />
          <div>
            <strong>分析服务未连接</strong>
            <span>{{ app.error }}。请确认 FastAPI 已在 8000 端口启动。</span>
          </div>
          <button class="btn btn-ghost btn-small" @click="app.load(true)">重试</button>
        </div>
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
        <footer class="global-footer">
          <span>HOUSEMIND AI / DECISION INTELLIGENCE</span>
          <span>历史数据 · 概率区间 · 非正式评估</span>
        </footer>
      </main>
    </div>
    <ToastStack />
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; display: flex; background: var(--paper); }
.sidebar {
  width: 252px; flex: 0 0 252px; height: 100vh; position: sticky; top: 0; z-index: 40;
  background: var(--ink-deep); color: var(--paper); display: flex; flex-direction: column;
  padding: 26px 18px 20px; border-right: 1px solid rgba(216,188,140,.12);
}
.brand { display: flex; align-items: center; gap: 11px; padding: 0 6px 28px; }
.brand-copy { min-width: 0; }
.brand-name { font-family: var(--font-sans); font-weight: 750; font-size: 13px; letter-spacing: .14em; white-space: nowrap; }
.brand-name span { color: var(--gold-light); }
.brand-sub { margin-top: 5px; font-size: 8px; letter-spacing: .18em; color: rgba(244,239,229,.44); }
.sidebar-close { display: none; margin-left: auto; color: var(--paper); }
.sidebar-section-label { padding: 0 10px 10px; font-size: 9px; letter-spacing: .2em; color: rgba(244,239,229,.32); }
.nav-list { display: flex; flex-direction: column; gap: 2px; }
.nav-item {
  position: relative; display: flex; align-items: center; gap: 10px; color: rgba(244,239,229,.62);
  padding: 11px 10px; border-radius: 5px; text-decoration: none; transition: background .22s ease, color .22s ease;
}
.nav-item:hover { color: var(--paper); background: rgba(244,239,229,.055); }
.nav-item.router-link-active { color: var(--paper); background: linear-gradient(90deg, rgba(216,188,140,.14), rgba(216,188,140,.02)); }
.nav-item.router-link-active::before {
  content: ''; position: absolute; left: 0; top: 9px; bottom: 9px; width: 2px; background: var(--gold-light); border-radius: 2px;
}
.nav-index { width: 19px; font-size: 8px; letter-spacing: .08em; color: rgba(244,239,229,.26); font-variant-numeric: tabular-nums; }
.nav-item.router-link-active .nav-index { color: var(--gold-light); }
.nav-icon { color: inherit; opacity: .9; }
.nav-copy { display: flex; flex-direction: column; min-width: 0; }
.nav-label { font-size: 12.5px; font-weight: 550; letter-spacing: .02em; }
.nav-short { margin-top: 2px; font-size: 9px; color: rgba(244,239,229,.3); letter-spacing: .03em; }
.nav-item.router-link-active .nav-short { color: rgba(244,239,229,.5); }
.sidebar-foot { margin-top: auto; padding: 0 8px; }
.model-status { display: flex; align-items: center; gap: 9px; }
.status-orbit { width: 22px; height: 22px; border: 1px solid rgba(216,188,140,.35); border-radius: 50%; display: grid; place-items: center; }
.status-dot { width: 5px; height: 5px; border-radius: 50%; background: #a9c8a9; box-shadow: 0 0 0 4px rgba(169,200,169,.08); }
.model-title { font-size: 8.5px; letter-spacing: .14em; color: rgba(244,239,229,.72); }
.model-meta { margin-top: 3px; font-size: 8px; color: rgba(244,239,229,.35); }
.sidebar-divider { height: 1px; background: rgba(244,239,229,.09); margin: 18px 0 15px; }
.sidebar-note { display: flex; gap: 8px; color: rgba(244,239,229,.46); font-size: 9.5px; line-height: 1.7; }
.sidebar-note svg { flex: 0 0 auto; margin-top: 2px; color: var(--gold); }
.sidebar-legal { margin-top: 18px; font-size: 7px; letter-spacing: .12em; line-height: 1.8; color: rgba(244,239,229,.2); }
.sidebar-scrim { display: none; }
.workspace { min-width: 0; flex: 1; }
.topbar {
  height: 72px; padding: 0 42px; display: flex; align-items: center; gap: 22px;
  border-bottom: 1px solid var(--line); background: rgba(244,239,229,.86); backdrop-filter: blur(14px);
  position: sticky; top: 0; z-index: 30;
}
.topbar-context { min-width: 0; }
.topbar-eyebrow { font-size: 8px; letter-spacing: .19em; color: var(--muted); }
.topbar-eyebrow span { color: var(--gold); margin: 0 4px; }
.topbar-title { font-family: var(--font-serif); font-size: 20px; font-weight: 550; letter-spacing: -.01em; margin-top: 2px; }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 17px; }
.mode-pill { display: flex; align-items: center; gap: 7px; font-size: 9px; letter-spacing: .06em; padding: 6px 10px; border: 1px solid var(--line); border-radius: 99px; color: var(--ink-soft); background: rgba(251,248,241,.6); }
.mode-dot { width: 5px; height: 5px; border-radius: 50%; }
.mode-pill.live .mode-dot { background: #4d8c63; box-shadow: 0 0 0 3px rgba(77,140,99,.12); }
.mode-pill.local .mode-dot { background: var(--gold); box-shadow: 0 0 0 3px rgba(176,138,82,.12); }
.topbar-period { font-size: 9px; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }
.topbar-period-label { font-size: 7px; letter-spacing: .16em; color: var(--gold); }
.topbar-cta { gap: 7px; }
.mobile-menu { display: none; }
.page-wrap { max-width: 1540px; margin: 0 auto; padding: 38px 42px 26px; }
.service-banner { display: flex; align-items: center; gap: 11px; border: 1px solid rgba(180,107,82,.35); background: rgba(180,107,82,.07); padding: 12px 15px; border-radius: 5px; margin-bottom: 22px; font-size: 12px; }
.service-banner-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--clay); flex: 0 0 auto; }
.service-banner div { display: flex; gap: 8px; align-items: baseline; flex: 1; }
.service-banner strong { font-weight: 650; }
.service-banner span { color: var(--muted); }
.global-footer { margin-top: 48px; padding-top: 17px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; font-size: 8px; letter-spacing: .12em; color: var(--muted-light); }
.page-enter-active, .page-leave-active { transition: opacity .24s ease, transform .24s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }
@media (max-width: 1120px) {
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-102%); transition: transform .28s cubic-bezier(.22,.8,.2,1); box-shadow: 24px 0 50px rgba(6,18,14,.22); }
  .sidebar.is-open { transform: translateX(0); }
  .sidebar-close, .mobile-menu { display: inline-flex; }
  .sidebar-scrim { display: block; position: fixed; inset: 0; z-index: 35; background: rgba(6,18,14,.45); backdrop-filter: blur(2px); }
  .topbar { padding: 0 24px; }
  .page-wrap { padding: 28px 24px 22px; }
}
@media (max-width: 760px) {
  .topbar { height: 64px; gap: 12px; padding: 0 16px; }
  .topbar-actions .topbar-period, .topbar-actions .mode-pill { display: none; }
  .topbar-cta { padding: 8px 11px; font-size: 10px; }
  .topbar-title { font-size: 17px; }
  .page-wrap { padding: 21px 15px 18px; }
  .global-footer { flex-direction: column; gap: 7px; }
}
</style>
