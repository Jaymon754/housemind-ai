<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRight,
  ArrowUpRight,
  BookMarked,
  ChevronRight,
  Database,
  FileText,
  Layers3,
  Library,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import { api } from '@/api'
import type { KnowledgeAnswer, KnowledgeResult, KnowledgeStats } from '@/types'
import { useToastStore } from '@/stores/toast'
import PageHeader from '@/components/PageHeader.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import EmptyState from '@/components/EmptyState.vue'

const toast = useToastStore()
const stats = ref<KnowledgeStats | null>(null)
const question = ref('首付比例和DSCR有什么关系？')
const activeQuestion = ref('')
const answer = ref<KnowledgeAnswer | null>(null)
const results = ref<KnowledgeResult[]>([])
const mode = ref<'answer' | 'search'>('answer')
const category = ref('')
const loading = ref(false)
const statsLoading = ref(true)
const error = ref('')
const readerOpen = ref(false)
const readerLoading = ref(false)
const reader = ref<{ doc_id: string; meta: Record<string, string>; markdown: string } | null>(null)
const hasAutoQueried = ref(false)

const corpusLede = computed(() => `${stats.value?.documents ?? 18} 篇方法文档、${stats.value?.chunks ?? 71} 个语义片段。Chroma 向量召回与 BM25 字面检索混合排序，回答必须携带可点击来源；检索不到就说不知道。`)

const suggestions = [
  'DSCR 低于 1.25 意味着什么？',
  'Cap Rate 和现金回报率有什么区别？',
  'AVM 估值为什么需要参考区间？',
  '照片分析能判断结构安全吗？',
  '1031 置换的基本条件是什么？',
]

const categories = computed(() => stats.value?.categories ?? [])
const docs = computed(() => {
  const list = stats.value?.documents_list ?? []
  if (!category.value) return list
  return list.filter((doc) => doc.category === category.value)
})
const maxScore = computed(() => Math.max(0.001, ...results.value.map((item) => item.score)))
const modeLabel = computed(() => {
  if (mode.value === 'search') return '仅检索模式'
  if (answer.value?.mode === 'deepseek') return 'DeepSeek 生成'
  return '本地抽取式回答'
})

async function loadStats() {
  statsLoading.value = true
  try {
    stats.value = await api.knowledgeStats()
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '知识库状态加载失败', 'error')
  } finally {
    statsLoading.value = false
  }
}

async function run(custom?: string) {
  const text = (custom ?? question.value).trim()
  if (text.length < 2) {
    toast.push('请输入至少 2 个字符的问题', 'error')
    return
  }
  question.value = text
  activeQuestion.value = text
  loading.value = true
  error.value = ''
  answer.value = null
  results.value = []
  try {
    if (mode.value === 'answer') {
      answer.value = await api.knowledgeQuery({ question: text, top_k: 6, category: category.value || null })
      results.value = answer.value.results
    } else {
      const data = await api.knowledgeSearch({ question: text, top_k: 8, category: category.value || null })
      results.value = data.results
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '检索失败，请稍后重试'
    toast.push(error.value, 'error')
  } finally {
    loading.value = false
  }
}

function chooseSuggestion(text: string) {
  mode.value = 'answer'
  run(text)
}

async function openDocument(docId: string) {
  readerOpen.value = true
  readerLoading.value = true
  reader.value = null
  try {
    reader.value = await api.knowledgeDocument(docId)
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '文档加载失败', 'error')
    readerOpen.value = false
  } finally {
    readerLoading.value = false
  }
}

function closeReader() {
  readerOpen.value = false
  reader.value = null
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.isComposing) run()
}

onMounted(async () => {
  await loadStats()
  if (!hasAutoQueried.value) {
    hasAutoQueried.value = true
    await run()
  }
})
</script>

<template>
  <div class="page knowledge-page">
    <PageHeader
      eyebrow="RAG KNOWLEDGE BASE / 05"
      title="让每一条结论，<em>都有出处</em>。"
      :lede="corpusLede"
    >
      <template #actions>
        <span class="badge badge-sage"><Database :size="11" /> {{ stats?.documents ?? '—' }} DOCS</span>
        <span class="badge badge-gold"><Layers3 :size="11" /> {{ stats?.chunks ?? '—' }} CHUNKS</span>
      </template>
    </PageHeader>

    <section class="ask-stage">
      <div class="ask-stage-head">
        <div>
          <div class="ask-kicker">ASK THE CORPUS</div>
          <h2>问一个具体的问题，<br /><em>而不是“介绍一下”。</em></h2>
        </div>
        <div class="ask-meta">
          <span><i />{{ stats?.backend ?? 'CHROMA' }} PERSISTENT</span>
          <span>512D SIGNED HASHING + BM25</span>
        </div>
      </div>

      <div class="search-box">
        <Search :size="18" class="search-icon" />
        <input
          v-model="question"
          type="text"
          maxlength="800"
          placeholder="例如：首付比例和 DSCR 有什么关系？"
          aria-label="知识库检索问题"
          @keydown="onKeydown"
        />
        <div class="search-mode" role="group" aria-label="检索模式">
          <button :class="{ active: mode === 'answer' }" @click="mode = 'answer'">问答</button>
          <button :class="{ active: mode === 'search' }" @click="mode = 'search'">仅检索</button>
        </div>
        <button class="ask-btn" :disabled="loading" @click="run()">
          <span v-if="loading" class="spinner light" />
          <Sparkles v-else :size="15" />
          {{ loading ? '检索中' : '提问' }}
        </button>
      </div>

      <div class="suggest-row">
        <span class="suggest-label">TRY</span>
        <button v-for="item in suggestions" :key="item" class="chip" @click="chooseSuggestion(item)">{{ item }}</button>
      </div>

      <div class="pipeline">
        <div class="pipeline-step">
          <span class="step-num">01</span>
          <div><strong>Query</strong><small>中文问题归一化与实体识别</small></div>
        </div>
        <ArrowRight :size="13" />
        <div class="pipeline-step">
          <span class="step-num">02</span>
          <div><strong>Hybrid Recall</strong><small>向量 {{ stats?.chunks ?? 71 }} 片段 + BM25 字符 n-gram</small></div>
        </div>
        <ArrowRight :size="13" />
        <div class="pipeline-step">
          <span class="step-num">03</span>
          <div><strong>Score Fusion</strong><small>关键词权重 · 标题覆盖 · 文档多样性</small></div>
        </div>
        <ArrowRight :size="13" />
        <div class="pipeline-step">
          <span class="step-num">04</span>
          <div><strong>Grounded Answer</strong><small>回答约束在 retrieved chunks 内</small></div>
        </div>
      </div>
    </section>

    <div class="knowledge-layout mt-24">
      <section class="answer-column">
        <div v-if="loading" class="card answer-loading">
          <div class="skeleton" style="width: 34%; height: 12px" />
          <div class="skeleton" style="width: 78%; height: 25px; margin-top: 14px" />
          <div class="skeleton" style="width: 100%; height: 10px; margin-top: 16px" />
          <div class="skeleton" style="width: 94%; height: 10px; margin-top: 8px" />
          <div class="skeleton" style="width: 87%; height: 10px; margin-top: 8px" />
          <div class="skeleton" style="width: 55%; height: 10px; margin-top: 8px" />
        </div>

        <div v-else-if="error" class="card">
          <EmptyState title="检索暂时失败" :description="error">
            <button class="btn btn-ghost btn-small mt-16" @click="run()">重新检索</button>
          </EmptyState>
        </div>

        <template v-else-if="results.length">
          <div v-if="answer" class="card answer-card">
            <div class="answer-head">
              <div>
                <div class="card-label">GROUNDED ANSWER</div>
                <div class="answer-question">{{ activeQuestion }}</div>
              </div>
              <span class="badge" :class="answer.mode === 'deepseek' ? 'badge-sage' : 'badge-gold'">{{ modeLabel }}</span>
            </div>
            <div class="answer-body">
              <MarkdownRenderer :content="answer.answer" />
            </div>
            <div class="answer-foot">
              <span><BookMarked :size="12" /> 回答仅基于下方 {{ answer.citations.length }} 条检索片段</span>
              <span v-if="answer.mode !== 'deepseek'">未配置 LLM 时使用透明抽取式回答，不编造段落</span>
            </div>
          </div>

          <div class="results-head">
            <div>
              <div class="card-label">{{ answer ? 'RETRIEVED EVIDENCE' : 'SEARCH RESULTS' }}</div>
              <h3 class="section-title">{{ results.length }} 个相关片段</h3>
            </div>
            <span class="badge badge-outline">{{ modeLabel }}</span>
          </div>

          <article v-for="(item, index) in results" :key="item.id" class="result-card card card-hover">
            <div class="result-rank">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="result-main">
              <div class="result-top">
                <div class="result-title-row">
                  <span class="badge badge-outline">{{ item.category_label }}</span>
                  <button class="result-title" @click="openDocument(item.doc_id)">{{ item.title }}</button>
                </div>
                <span class="result-score" :title="`混合检索得分 ${item.score}`">{{ item.score.toFixed(2) }}</span>
              </div>
              <div class="result-section">{{ item.section }}</div>
              <p class="result-snippet">{{ item.snippet }}</p>
              <div class="result-foot">
                <span>{{ item.source_name }}</span>
                <span class="result-scorebar"><i :style="{ width: `${(item.score / maxScore) * 100}%` }" /></span>
                <button class="result-open" @click="openDocument(item.doc_id)">阅读全文 <ArrowUpRight :size="11" /></button>
              </div>
            </div>
          </article>
        </template>

        <div v-else class="card">
          <EmptyState title="输入一个具体问题" description="系统会先检索，再回答。不会脱离资料编造来源。" />
        </div>
      </section>

      <aside class="side-column">
        <div v-if="answer" class="card citations-card">
          <div class="card-head">
            <div>
              <div class="card-label">CITATIONS</div>
              <h3 class="card-title">可核对的来源</h3>
            </div>
            <span class="citation-count">{{ answer.citations.length }}</span>
          </div>
          <a
            v-for="citation in answer.citations"
            :key="citation.index"
            class="side-citation"
            :href="citation.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span class="side-index">{{ citation.index }}</span>
            <span class="side-copy">
              <strong>{{ citation.title }}</strong>
              <small>{{ citation.section }}</small>
              <em>{{ citation.source_name }}</em>
            </span>
            <ArrowUpRight :size="12" />
          </a>
          <p class="citation-note">来源链接指向公开机构页面。项目文档为方法摘要，不替代原始法规或评估标准。</p>
        </div>

        <div class="card corpus-card">
          <div class="card-head">
            <div>
              <div class="card-label">CORPUS MAP</div>
              <h3 class="card-title">语料分布</h3>
            </div>
            <Library :size="16" class="corpus-icon" />
          </div>
          <div class="category-list">
            <button
              v-for="cat in categories"
              :key="cat.key"
              class="category-row"
              :class="{ active: category === cat.key }"
              @click="category = category === cat.key ? '' : cat.key"
            >
              <span>{{ cat.label }}</span>
              <i><b :style="{ width: `${(cat.count / Math.max(1, stats?.documents ?? 1)) * 100}%` }" /></i>
              <strong>{{ cat.count }}</strong>
            </button>
          </div>
          <button v-if="category" class="clear-filter" @click="category = ''">清除筛选 · 显示全部</button>
          <div class="corpus-note">
            <Database :size="11" />
            <span>{{ stats?.embedding }}<br />索引于 {{ stats?.indexed_at?.slice(0, 10) }}</span>
          </div>
        </div>

        <div class="card scope-card">
          <div class="card-label">SCOPE & LIMITS</div>
          <p>知识库覆盖美国住宅估值、房贷、投资、交易、税务与 AI 安全，不构成中国购房政策或个案法律意见。</p>
          <div class="scope-tags"><span>美国住宅</span><span>方法说明</span><span>可追溯</span></div>
        </div>
      </aside>
    </div>

    <section class="library-section mt-32">
      <div class="section-head">
        <div>
          <div class="section-kicker">DOCUMENT LIBRARY</div>
          <h2 class="section-title">方法文档库 <span class="doc-count">{{ docs.length }} / {{ stats?.documents ?? 0 }}</span></h2>
          <p class="section-desc">每篇文档拆成多个语义片段进入索引；点击可阅读原始 Markdown。</p>
        </div>
        <div class="library-filter">
          <button class="chip" :class="{ active: category === '' }" @click="category = ''">全部</button>
          <button v-for="cat in categories.slice(0, 6)" :key="cat.key" class="chip" :class="{ active: category === cat.key }" @click="category = cat.key">{{ cat.label }}</button>
        </div>
      </div>

      <div v-if="statsLoading" class="doc-grid">
        <div v-for="i in 6" :key="i" class="skeleton doc-skeleton" />
      </div>
      <div v-else class="doc-grid">
        <button v-for="doc in docs" :key="doc.doc_id" class="doc-card" @click="openDocument(doc.doc_id)">
          <div class="doc-top">
            <span class="doc-category">{{ doc.category_label }}</span>
            <FileText :size="15" class="doc-icon" />
          </div>
          <h3>{{ doc.title }}</h3>
          <div class="doc-meta"><span>{{ doc.sections }} 个片段</span><span>{{ doc.source_name }}</span></div>
          <div class="doc-open">阅读文档 <ChevronRight :size="12" /></div>
        </button>
      </div>
    </section>

    <Transition name="drawer">
      <div v-if="readerOpen" class="reader-layer">
        <div class="reader-scrim" @click="closeReader" />
        <aside class="reader-panel">
          <div class="reader-head">
            <div>
              <div class="card-label">SOURCE DOCUMENT</div>
              <div class="reader-title">{{ reader?.meta.title ?? '正在载入' }}</div>
            </div>
            <button class="icon-btn" aria-label="关闭文档" @click="closeReader"><X :size="18" /></button>
          </div>
          <div v-if="readerLoading" class="reader-loading"><span class="spinner" /> 读取 Markdown</div>
          <div v-else-if="reader" class="reader-body">
            <div class="reader-meta">
              <span>{{ reader.meta.category }}</span>
              <span>{{ reader.meta.source_name }}</span>
              <span>更新于 {{ reader.meta.updated }}</span>
            </div>
            <MarkdownRenderer :content="reader.markdown" />
            <a class="reader-source" :href="reader.meta.source_url" target="_blank" rel="noopener noreferrer">
              查看原始来源 <ArrowUpRight :size="13" />
            </a>
          </div>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.ask-stage { background: var(--ink); color: var(--paper); border-radius: 10px; padding: 26px 28px 0; overflow: hidden; position: relative; }
.ask-stage::after { content: ''; position: absolute; right: -60px; top: -100px; width: 380px; height: 380px; border: 1px solid rgba(119,168,212,.1); border-radius: 50%; pointer-events: none; }
.ask-stage-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 25px; position: relative; z-index: 1; }
.ask-kicker { font-size: 7.5px; letter-spacing: .2em; color: var(--gold-light); }
.ask-stage h2 { font-family: var(--font-serif); font-size: clamp(24px, 2.4vw, 34px); font-weight: 650; letter-spacing: -.03em; line-height: 1.18; margin-top: 9px; }
.ask-stage h2 em { color: var(--gold-light); font-weight: 380; }
.ask-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; font-size: 6.5px; letter-spacing: .12em; color: rgba(248,250,252,.35); }
.ask-meta span { display: inline-flex; align-items: center; gap: 5px; }
.ask-meta i { width: 4px; height: 4px; border-radius: 50%; background: var(--sage-light); }
.search-box { display: flex; align-items: center; gap: 11px; background: var(--paper-2); border-radius: 8px; padding: 7px 8px 7px 15px; margin-top: 21px; position: relative; z-index: 2; }
.search-icon { color: var(--gold); flex: 0 0 auto; }
.search-box input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; font-size: 12.5px; height: 33px; }
.search-box input::placeholder { color: var(--muted-light); }
.search-mode { display: flex; background: var(--paper-3); border-radius: 7px; padding: 2px; flex: 0 0 auto; }
.search-mode button { border: 0; background: transparent; padding: 5px 8px; font-size: 8px; color: var(--muted); border-radius: 6px; }
.search-mode button.active { background: var(--paper-2); color: var(--ink); box-shadow: 0 1px 3px rgba(15,23,42,.08); }
.ask-btn { display: inline-flex; align-items: center; gap: 6px; height: 35px; padding: 0 14px; border-radius: 7px; border: 0; background: var(--ink); color: var(--paper); font-size: 9.5px; font-weight: 650; flex: 0 0 auto; }
.ask-btn:hover { background: #1c3a30; }
.suggest-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 12px; position: relative; z-index: 2; }
.suggest-label { font-size: 6.5px; letter-spacing: .15em; color: rgba(248,250,252,.33); margin-right: 2px; }
.suggest-row .chip { border-color: rgba(248,250,252,.16); color: rgba(248,250,252,.55); background: transparent; font-size: 7.5px; padding: 4px 8px; }
.suggest-row .chip:hover { border-color: var(--gold-light); color: var(--paper); }
.pipeline { display: flex; align-items: center; gap: 8px; margin: 20px -28px 0; padding: 13px 28px; border-top: 1px solid rgba(248,250,252,.11); background: rgba(248,250,252,.025); position: relative; z-index: 1; overflow-x: auto; }
.pipeline-step { display: flex; align-items: center; gap: 7px; flex: 1; min-width: 150px; }
.step-num { font-family: var(--font-serif); font-size: 15px; color: var(--gold-light); opacity: .7; }
.pipeline-step div { display: flex; flex-direction: column; gap: 1px; }
.pipeline-step strong { font-size: 8px; letter-spacing: .05em; }
.pipeline-step small { font-size: 6.5px; color: rgba(248,250,252,.33); white-space: nowrap; }
.pipeline > svg { color: rgba(248,250,252,.2); flex: 0 0 auto; }

.knowledge-layout { display: grid; grid-template-columns: minmax(0, 1fr) 292px; gap: 18px; align-items: start; }
.answer-column { min-width: 0; }
.answer-card { padding: 22px 23px 17px; }
.answer-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 13px; border-bottom: 1px solid var(--line); }
.answer-question { font-family: var(--font-serif); font-size: 20px; font-weight: 650; letter-spacing: -.02em; margin-top: 5px; }
.answer-body { padding: 11px 0 3px; }
.answer-foot { display: flex; justify-content: space-between; gap: 13px; padding-top: 11px; border-top: 1px solid var(--line-soft); font-size: 7.5px; color: var(--muted-light); }
.answer-foot span { display: inline-flex; align-items: center; gap: 4px; }
.answer-loading { padding: 25px; min-height: 250px; }
.results-head { display: flex; justify-content: space-between; align-items: flex-end; margin: 23px 0 12px; }
.results-head .section-title { font-size: 21px; }
.result-card { display: flex; gap: 14px; padding: 15px 17px; margin-bottom: 8px; }
.result-rank { font-family: var(--font-serif); font-size: 20px; color: var(--line); line-height: 1; flex: 0 0 auto; width: 23px; }
.result-main { min-width: 0; flex: 1; }
.result-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.result-title-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.result-title { border: 0; background: none; padding: 0; font-family: var(--font-serif); font-size: 15.5px; font-weight: 650; letter-spacing: -.015em; text-align: left; }
.result-title:hover { color: var(--gold); }
.result-score { font-size: 8px; color: var(--muted-light); border: 1px solid var(--line); border-radius: 6px; padding: 2px 5px; flex: 0 0 auto; }
.result-section { font-size: 8px; color: var(--gold); margin-top: 3px; letter-spacing: .03em; }
.result-snippet { font-size: 9.5px; line-height: 1.7; color: var(--muted); margin-top: 6px; }
.result-foot { display: flex; align-items: center; gap: 10px; margin-top: 8px; font-size: 7.5px; color: var(--muted-light); }
.result-scorebar { flex: 1; max-width: 150px; height: 2px; background: var(--paper-3); border-radius: 6px; overflow: hidden; }
.result-scorebar i { display: block; height: 100%; background: linear-gradient(90deg, var(--sage), var(--gold)); }
.result-open { margin-left: auto; display: inline-flex; align-items: center; gap: 3px; border: 0; background: none; font-size: 7.5px; color: var(--ink-soft); }
.result-open:hover { color: var(--gold); }

.side-column { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 92px; }
.citations-card { padding: 18px 16px 15px; }
.citation-count { font-family: var(--font-serif); font-size: 25px; color: var(--gold); line-height: 1; }
.side-citation { display: flex; align-items: flex-start; gap: 8px; padding: 9px 0; border-bottom: 1px solid var(--line-soft); text-decoration: none; }
.side-citation:last-of-type { border-bottom: 0; }
.side-index { width: 17px; height: 17px; border-radius: 50%; border: 1px solid var(--line); display: grid; place-items: center; font-size: 7px; color: var(--muted); flex: 0 0 auto; margin-top: 1px; }
.side-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.side-copy strong { font-size: 8.5px; line-height: 1.4; font-weight: 620; }
.side-copy small { font-size: 7px; color: var(--gold); }
.side-copy em { font-style: normal; font-size: 6.5px; color: var(--muted-light); }
.side-citation > svg { color: var(--muted-light); flex: 0 0 auto; margin-top: 2px; }
.side-citation:hover .side-copy strong { color: var(--gold); }
.citation-note { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--line-soft); font-size: 6.5px; line-height: 1.6; color: var(--muted-light); }
.corpus-icon { color: var(--gold); }
.category-list { display: flex; flex-direction: column; gap: 2px; }
.category-row { display: grid; grid-template-columns: 53px 1fr 17px; align-items: center; gap: 7px; border: 0; background: transparent; padding: 4px 3px; border-radius: 6px; text-align: left; }
.category-row:hover, .category-row.active { background: rgba(29,90,150,.08); }
.category-row span { font-size: 7.5px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.category-row i { height: 2px; background: var(--paper-3); border-radius: 6px; overflow: hidden; }
.category-row b { display: block; height: 100%; background: var(--sage); }
.category-row strong { font-size: 7px; color: var(--muted-light); text-align: right; }
.clear-filter { margin-top: 7px; border: 0; background: none; font-size: 7px; color: var(--gold); padding: 0; }
.corpus-note { display: flex; align-items: flex-start; gap: 5px; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line-soft); font-size: 6.5px; line-height: 1.55; color: var(--muted-light); }
.corpus-note svg { flex: 0 0 auto; color: var(--sage); margin-top: 1px; }
.scope-card p { font-size: 8px; line-height: 1.7; color: var(--muted); margin-top: 7px; }
.scope-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 9px; }
.scope-tags span { font-size: 6.5px; border: 1px solid var(--line); padding: 2px 5px; border-radius: 99px; color: var(--muted-light); }

.library-section { border-top: 1px solid var(--line); padding-top: 27px; }
.library-filter { display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; max-width: 560px; }
.doc-count { font-family: var(--font-sans); font-size: 9px; color: var(--muted-light); letter-spacing: 0; margin-left: 5px; }
.doc-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.doc-card { text-align: left; border: 1px solid var(--line); background: #ffffff; border-radius: 8px; padding: 15px; min-height: 154px; display: flex; flex-direction: column; transition: border-color .2s, background .2s, transform .2s; }
.doc-card:hover { border-color: var(--gold); background: var(--paper-2); transform: translateY(-2px); }
.doc-top { display: flex; justify-content: space-between; align-items: center; }
.doc-category { font-size: 6.5px; letter-spacing: .1em; color: var(--gold); text-transform: uppercase; }
.doc-icon { color: var(--muted-light); }
.doc-card h3 { font-family: var(--font-serif); font-size: 15px; font-weight: 650; line-height: 1.35; letter-spacing: -.015em; margin-top: 10px; }
.doc-meta { display: flex; justify-content: space-between; gap: 8px; margin-top: auto; padding-top: 12px; font-size: 6.5px; color: var(--muted-light); }
.doc-meta span:last-child { text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-open { display: flex; align-items: center; gap: 2px; margin-top: 7px; font-size: 7px; color: var(--muted); }
.doc-skeleton { height: 154px; }

.reader-layer { position: fixed; inset: 0; z-index: 80; }
.reader-scrim { position: absolute; inset: 0; background: rgba(6,18,14,.42); backdrop-filter: blur(2px); }
.reader-panel { position: absolute; right: 0; top: 0; bottom: 0; width: min(680px, 92vw); background: var(--paper-2); border-left: 1px solid var(--line); box-shadow: -20px 0 60px rgba(15,23,42,.16); display: flex; flex-direction: column; }
.reader-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 15px; padding: 20px 24px 16px; border-bottom: 1px solid var(--line); }
.reader-title { font-family: var(--font-serif); font-size: 22px; font-weight: 650; letter-spacing: -.02em; margin-top: 5px; }
.reader-loading { display: flex; align-items: center; gap: 8px; padding: 35px 24px; font-size: 10px; color: var(--muted); }
.reader-body { overflow-y: auto; padding: 23px 24px 45px; }
.reader-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 18px; }
.reader-meta span { font-size: 7px; border: 1px solid var(--line); border-radius: 6px; padding: 3px 6px; color: var(--muted); }
.reader-source { display: inline-flex; align-items: center; gap: 4px; margin-top: 25px; padding-top: 13px; border-top: 1px solid var(--line); font-size: 8.5px; color: var(--gold); text-decoration: none; }
.drawer-enter-active, .drawer-leave-active { transition: opacity .22s; }
.drawer-enter-active .reader-panel, .drawer-leave-active .reader-panel { transition: transform .3s cubic-bezier(.22,.8,.2,1); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .reader-panel, .drawer-leave-to .reader-panel { transform: translateX(100%); }

@media (max-width: 1100px) {
  .knowledge-layout { grid-template-columns: 1fr; }
  .side-column { position: static; display: grid; grid-template-columns: 1fr 1fr; }
  .scope-card { grid-column: 1 / -1; }
  .doc-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 760px) {
  .ask-stage { padding: 20px 17px 0; }
  .ask-stage-head { flex-direction: column; gap: 10px; }
  .ask-meta { align-items: flex-start; }
  .search-box { flex-wrap: wrap; gap: 7px; padding: 8px 9px 8px 12px; }
  .search-box input { width: 100%; flex: 1 0 calc(100% - 30px); height: 28px; }
  .search-mode { margin-left: 25px; }
  .ask-btn { margin-left: auto; }
  .pipeline { margin: 16px -17px 0; padding: 12px 17px; gap: 10px; display: grid; grid-template-columns: 1fr 1fr; overflow: visible; }
  .pipeline-step { min-width: 0; }
  .pipeline > svg { display: none; }
  .side-column { grid-template-columns: 1fr; }
  .scope-card { grid-column: auto; }
  .doc-grid { grid-template-columns: 1fr; }
  .library-filter { justify-content: flex-start; }
  .result-card { padding: 12px; gap: 9px; }
  .result-rank { font-size: 16px; width: 19px; }
  .answer-foot { flex-direction: column; gap: 4px; }
}
</style>
