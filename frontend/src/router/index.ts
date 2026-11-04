import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0, behavior: 'smooth' }),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { title: '数据驾驶舱', eyebrow: 'MARKET INTELLIGENCE', index: '01' },
    },
    {
      path: '/valuation',
      name: 'valuation',
      component: () => import('@/views/ValuationView.vue'),
      meta: { title: '智能估值', eyebrow: 'VALUATION STUDIO', index: '02' },
    },
    {
      path: '/investment',
      name: 'investment',
      component: () => import('@/views/InvestmentView.vue'),
      meta: { title: '投资决策', eyebrow: 'INVESTMENT UNDERWRITING', index: '03' },
    },
    {
      path: '/agent',
      name: 'agent',
      component: () => import('@/views/AgentView.vue'),
      meta: { title: 'AI 顾问', eyebrow: 'AGENT WORKSPACE', index: '04' },
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('@/views/KnowledgeView.vue'),
      meta: { title: '知识库', eyebrow: 'RAG KNOWLEDGE BASE', index: '05' },
    },
    {
      path: '/vision',
      name: 'vision',
      component: () => import('@/views/VisionView.vue'),
      meta: { title: '图像分析', eyebrow: 'MULTIMODAL VISION', index: '06' },
    },
    {
      path: '/research',
      name: 'research',
      component: () => import('@/views/ResearchView.vue'),
      meta: { title: '研究实验室', eyebrow: 'MODEL RESEARCH', index: '07' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? 'HouseMind AI')} · HouseMind AI`
})

export default router
