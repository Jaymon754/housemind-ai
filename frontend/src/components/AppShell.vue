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
  width: 248px; flex: 0 0 248px; height: 100vh; position: sticky; top: 0; z-index: 40;
  background: var(--ink-deep); color: #f8fafc; display: flex; flex-direction: column;
  padding: 24px 16px 18px; border-right: 1px solid rgba(255,255,255,.07);
}
.brand { display: flex; align-items: center; gap: 11px; padding: 0 6px 26px; border-bottom: 1px solid rgba(255,255,255,.08); margin-bottom: 20px; }
.brand-copy { min-width: 0; }
.brand-name { font-weight: 750; font-size: 13px; letter-spacing: .12em; white-space: nowrap; }
.brand-name span { color: #9ec5e6; }
.brand-sub { margin-top: 4px; font-size: 8px; letter-spacing: .13em; color: rgba(248,250,252,.42); }
.sidebar-close { display: none; margin-left: auto; color: #f8fafc; }
.sidebar-section-label { padding: 0 10px 9px; font-size: 9px; font-weight: 650; letter-spacing: .14em; color: rgba(248,250,252,.34); }
.nav-list { display: flex; flex-direction: column; gap: 3px; }
.nav-item {
  position: relative; display: flex; align-items: center; gap: 11px; color: rgba(248,250,252,.66);
  padding: 10px 11px; border-radius: 8px; text-decoration: none; transition: background .18s ease, color .18s ease;
}
.nav-item:hover { color: #fff; background: rgba(255,255,255,.06); }
.nav-item.router-link-active { color: #fff; background: #14324a; }
.nav-item.router-link-active::before {
  content: ''; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; background: #60a5fa; border-radius: 0 3px 3px 0;
}
.nav-index { display: none; }
.nav-icon { color: inherit; opacity: .92; }
.nav-copy { display: flex; flex-direction: column; min-width: 0; }
.nav-label { font-size: 13px; font-weight: 600; letter-spacing: .01em; }
.nav-short { margin-top: 1px; font-size: 9.5px; color: rgba(248,250,252,.34); letter-spacing: .01em; }
.nav-item.router-link-active .nav-short { color: rgba(248,250,252,.56); }
.sidebar-foot { margin-top: auto; padding: 0 7px; }
.model-status { display: flex; align-items: center; gap: 9px; }
.status-orbit { width: 22px; height: 22px; border: 1px solid rgba(158,197,230,.32); border-radius: 7px; display: grid; place-items: center; }
.status-dot { width: 5px; height: 5px; border-radius: 50%; background: #5eead4; box-shadow: 0 0 0 4px rgba(94,234,212,.08); }
.model-title { font-size: 8.5px; font-weight: 650; letter-spacing: .1em; color: rgba(248,250,252,.74); }
.model-meta { margin-top: 2px; font-size: 8.5px; color: rgba(248,250,252,.38); }
.sidebar-divider { height: 1px; background: rgba(255,255,255,.08); margin: 16px 0 13px; }
.sidebar-note { display: flex; gap: 8px; color: rgba(248,250,252,.48); font-size: 9.5px; line-height: 1.65; }
.sidebar-note svg { flex: 0 0 auto; margin-top: 2px; color: #9ec5e6; }
.sidebar-legal { margin-top: 16px; font-size: 7px; letter-spacing: .08em; line-height: 1.8; color: rgba(248,250,252,.24); }
.sidebar-scrim { display: none; }
.workspace { min-width: 0; flex: 1; }
.topbar {
  height: 64px; padding: 0 34px; display: flex; align-items: center; gap: 20px;
  border-bottom: 1px solid var(--line); background: rgba(255,255,255,.92); backdrop-filter: blur(14px);
  position: sticky; top: 0; z-index: 30;
}
.topbar-context { min-width: 0; }
.topbar-eyebrow { font-size: 9px; font-weight: 600; letter-spacing: .1em; color: var(--muted); }
.topbar-eyebrow span { color: var(--gold); margin: 0 5px; }
.topbar-title { font-family: var(--font-sans); font-size: 17px; font-weight: 700; letter-spacing: -.015em; margin-top: 1px; }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.mode-pill { display: flex; align-items: center; gap: 7px; font-size: 10px; font-weight: 600; letter-spacing: .01em; padding: 6px 10px; border: 1px solid var(--line); border-radius: 6px; color: var(--ink-soft); background: #f8fafc; }
.mode-dot { width: 5px; height: 5px; border-radius: 50%; }
.mode-pill.live .mode-dot { background: #0f766e; box-shadow: 0 0 0 3px rgba(15,118,110,.1); }
.mode-pill.local .mode-dot { background: #b45309; box-shadow: 0 0 0 3px rgba(180,83,9,.1); }
.topbar-period { font-size: 10px; color: var(--muted); display: flex; flex-direction: column; gap: 1px; }
.topbar-period-label { font-size: 8px; font-weight: 700; letter-spacing: .1em; color: var(--gold); }
.topbar-cta { gap: 7px; }
.mobile-menu { display: none; }
.page-wrap { max-width: 1500px; margin: 0 auto; padding: 30px 34px 24px; }
.service-banner { display: flex; align-items: center; gap: 11px; border: 1px solid #f1c4be; background: #fff7f6; padding: 11px 14px; border-radius: 8px; margin-bottom: 20px; font-size: 12px; }
.service-banner-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--clay); flex: 0 0 auto; }
.service-banner div { display: flex; gap: 8px; align-items: baseline; flex: 1; }
.service-banner strong { font-weight: 650; }
.service-banner span { color: var(--muted); }
.global-footer { margin-top: 42px; padding-top: 15px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; font-size: 9px; letter-spacing: .04em; color: var(--muted-light); }
.page-enter-active, .page-leave-active { transition: opacity .2s ease, transform .2s ease; }
.page-enter-from { opacity: 0; transform: translateY(5px); }
.page-leave-to { opacity: 0; transform: translateY(-3px); }
@media (max-width: 1120px) {
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-102%); transition: transform .28s cubic-bezier(.22,.8,.2,1); box-shadow: 20px 0 45px rgba(8,20,33,.24); }
  .sidebar.is-open { transform: translateX(0); }
  .sidebar-close, .mobile-menu { display: inline-flex; }
  .sidebar-scrim { display: block; position: fixed; inset: 0; z-index: 35; background: rgba(8,20,33,.48); backdrop-filter: blur(2px); }
  .topbar { padding: 0 24px; }
  .page-wrap { padding: 26px 24px 20px; }
}
@media (max-width: 760px) {
  .topbar { height: 60px; gap: 12px; padding: 0 16px; }
  .topbar-actions .topbar-period, .topbar-actions .mode-pill { display: none; }
  .topbar-cta { padding: 8px 11px; font-size: 10px; }
  .topbar-title { font-size: 16px; }
  .page-wrap { padding: 20px 15px 18px; }
  .global-footer { flex-direction: column; gap: 6px; }
}
</style>