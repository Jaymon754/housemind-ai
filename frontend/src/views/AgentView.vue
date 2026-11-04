<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, ref, watch, type Component } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowUp,
  BookOpen,
  Bot,
  Building2,
  Calculator,
  ChevronRight,
  History,
  ImagePlus,
  MapPin,
  MessageSquarePlus,
  ScanEye,
  Send,
  ShieldCheck,
  Sparkles,
  Square,
  Wrench,
  X,
} from 'lucide-vue-next'
import { api } from '@/api'
import { streamAgent } from '@/api/agent'
import type { AgentConversation, AgentToolCall, ChatMessage, Citation, Meta } from '@/types'
import { useAppStore } from '@/stores/app'
import { useAnalysisStore } from '@/stores/analysis'
import { useToastStore } from '@/stores/toast'
import { dateCN, timeCN } from '@/lib/format'
import PageHeader from '@/components/PageHeader.vue'
import AgentToolTrace from '@/components/AgentToolTrace.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const app = useAppStore()
const analysisStore = useAnalysisStore()
const toast = useToastStore()
const route = useRoute()

const messages = ref<ChatMessage[]>([])
const conversations = ref<AgentConversation[]>([])
const conversationId = ref<string | null>(null)
const composer = ref('')
const streaming = ref(false)
const currentStatus = ref('')
const sessionMode = ref('local')
const suggestions = ref<string[]>([])
const loadingHistory = ref(false)
const mobileHistory = ref(false)
const uploading = ref(false)
const imageId = ref<string | null>(null)
const imagePreview = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const textarea = ref<HTMLTextAreaElement | null>(null)
const messageList = ref<HTMLDivElement | null>(null)
let controller: AbortController | null = null
let scrollScheduled = false

const modeLabel = computed(() => (sessionMode.value === 'deepseek' ? 'DeepSeek Agent' : '本地规划器'))
const modeDescription = computed(() =>
  sessionMode.value === 'deepseek'
    ? 'DeepSeek Function Calling · 自主选择工具'
    : '确定性工具链 · 无密钥也可完整演示',
)
const activeTools = computed(() => messages.value.reduce((sum, msg) => sum + (msg.toolCalls?.length ?? 0), 0))
const activeCitations = computed(() => messages.value.reduce((sum, msg) => sum + (msg.citations?.length ?? 0), 0))
const tools = computed(() => app.meta?.tools ?? [])

const promptCards = markRaw([
  {
    icon: Building2,
    kicker: 'BUY OR WALK',
    title: '40 万美元预算，房价是否合理？',
    prompt: '我准备购买一套预算 40 万美元的房子，想了解房价是否合理，以及未来出租是否值得。',
  },
  {
    icon: Calculator,
    kicker: 'CASH FLOW',
    title: '首付与 DSCR 会怎样影响现金流？',
    prompt: '首付 25%、月租 3,200 美元，一套 68.5 万美元的房子 DSCR 和月现金流大概怎样？',
  },
  {
    icon: BookOpen,
    kicker: 'KNOWLEDGE',
    title: 'DSCR 和首付比例是什么关系？',
    prompt: '首付比例和 DSCR 有什么关系？请用知识库解释，并给出提高 DSCR 的方法。',
  },
  {
    icon: ScanEye,
    kicker: 'VISION BOUNDARY',
    title: '照片能判断结构安全吗？',
    prompt: '房屋照片能判断结构安全吗？图像分析可以看什么、不能看什么？',
  },
])

const toolIconMap: Record<string, Component> = {
  predict_house_price: Building2,
  explain_house_price: Sparkles,
  analyze_market: MapPin,
  calculate_investment: Calculator,
  search_property_knowledge: BookOpen,
  analyze_house_image: ScanEye,
}
function toolIcon(name: string): Component {
  return toolIconMap[name] ?? Wrench
}

interface HistoryMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode?: string
  meta?: {
    citations?: Citation[]
    tools?: string[]
    tool_records?: {
      name: string
      label?: string
      arguments?: Record<string, unknown>
      summary?: string
      latency_ms?: number
    }[]
  }
  created_at?: string
}

function makeId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
}

function scheduleScroll() {
  if (scrollScheduled) return
  scrollScheduled = true
  requestAnimationFrame(() => {
    scrollScheduled = false
    if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
  })
}

watch(messages, scheduleScroll, { deep: true })
watch(composer, () => {
  nextTick(() => {
    if (!textarea.value) return
    textarea.value.style.height = 'auto'
    textarea.value.style.height = `${Math.min(118, textarea.value.scrollHeight)}px`
  })
})

async function loadConversations() {
  try {
    const data = await api.conversations()
    conversations.value = data.items
  } catch {
    /* silent: chat remains usable */
  }
}

async function loadConversation(id: string) {
  if (streaming.value) stop()
  loadingHistory.value = true
  mobileHistory.value = false
  try {
    const data = (await api.conversation(id)) as { messages: HistoryMessage[] }
    conversationId.value = id
    messages.value = data.messages.map((item) => ({
      id: item.id,
      role: item.role,
      content: item.content,
      mode: item.mode,
      createdAt: item.created_at,
      citations: item.meta?.citations ?? [],
      toolCalls: (item.meta?.tool_records ?? []).map((tool) => ({
        id: makeId(),
        name: tool.name,
        label: tool.label ?? tool.name,
        arguments: tool.arguments ?? {},
        reason: '来自会话历史记录',
        status: 'done' as const,
        summary: tool.summary,
        latency_ms: tool.latency_ms,
      })),
      status: 'done',
    }))
    sessionMode.value = data.messages.at(-1)?.mode === 'deepseek' ? 'deepseek' : 'local'
    suggestions.value = []
    await nextTick()
    scheduleScroll()
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '无法载入会话', 'error')
  } finally {
    loadingHistory.value = false
  }
}

function newChat() {
  if (streaming.value) stop()
  messages.value = []
  conversationId.value = null
  suggestions.value = []
  imageId.value = null
  imagePreview.value = ''
  mobileHistory.value = false
  nextTick(() => textarea.value?.focus())
}

function findAssistant(id: string): ChatMessage | undefined {
  return messages.value.find((msg) => msg.id === id)
}

function updateAssistant(id: string, patch: Partial<ChatMessage>) {
  const assistant = findAssistant(id)
  if (assistant) Object.assign(assistant, patch)
  scheduleScroll()
}

function addToolCall(assistantId: string, call: Omit<AgentToolCall, 'id' | 'status'>) {
  const assistant = findAssistant(assistantId)
  if (!assistant) return
  if (!assistant.toolCalls) assistant.toolCalls = []
  assistant.toolCalls.push({ ...call, id: makeId(), status: 'running' })
  scheduleScroll()
}

function resolveToolCall(assistantId: string, name: string, patch: Partial<AgentToolCall>) {
  const assistant = findAssistant(assistantId)
  if (!assistant?.toolCalls) return
  const call = [...assistant.toolCalls].reverse().find((item) => item.name === name && item.status === 'running')
  if (call) Object.assign(call, patch)
  scheduleScroll()
}

async function send(prompt?: string) {
  if (streaming.value) return
  const text = (prompt ?? composer.value).trim()
  if (!text && !imageId.value) return
  if (text.length > 2000) {
    toast.push('单条消息请控制在 2,000 字以内', 'error')
    return
  }
  const attachedPreview = imagePreview.value
  const attachedId = imageId.value
  const userMessage: ChatMessage = {
    id: makeId(),
    role: 'user',
    content: text || '请分析这张房屋图片',
    createdAt: new Date().toISOString(),
    imagePreview: attachedPreview || undefined,
    status: 'done',
  }
  const assistantMessage: ChatMessage = {
    id: makeId(),
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    toolCalls: [],
    citations: [],
    status: 'streaming',
  }
  messages.value.push(userMessage, assistantMessage)
  composer.value = ''
  imageId.value = null
  imagePreview.value = ''
  suggestions.value = []
  currentStatus.value = '正在建立分析会话'
  streaming.value = true
  const assistantId = assistantMessage.id
  controller = new AbortController()
  await nextTick()
  scheduleScroll()

  try {
    await streamAgent(
      {
        message: text || '请分析这张房屋图片',
        conversation_id: conversationId.value,
        image_id: attachedId,
      },
      {
        onMeta: (data) => {
          conversationId.value = data.conversation_id
          sessionMode.value = data.mode
          if (data.guard?.severity === 'blocked' || data.guard?.severity === 'high') {
            currentStatus.value = '安全策略正在检查这次请求'
          }
        },
        onStatus: (data) => {
          currentStatus.value = data.label
        },
        onToolCall: (data) => {
          addToolCall(assistantId, {
            name: data.name,
            label: data.label,
            arguments: data.arguments,
            reason: data.reason,
          })
          currentStatus.value = `正在执行：${data.label}`
        },
        onToolResult: (data) => {
          resolveToolCall(assistantId, data.name, {
            status: 'done',
            summary: data.summary,
            latency_ms: data.latency_ms,
            data: data.data,
          })
        },
        onToolError: (data) => {
          resolveToolCall(assistantId, data.name, { status: 'error', error: data.message })
        },
        onToken: (chunk) => {
          const assistant = findAssistant(assistantId)
          if (!assistant) return
          assistant.content += chunk
          currentStatus.value = ''
          scheduleScroll()
        },
        onCitations: (citations) => {
          updateAssistant(assistantId, { citations })
        },
        onDone: (data) => {
          updateAssistant(assistantId, { status: 'done', mode: data.mode })
          sessionMode.value = data.mode
          conversationId.value = data.conversation_id
          suggestions.value = data.suggestions ?? []
          currentStatus.value = ''
          loadConversations()
        },
      },
      controller.signal,
    )
    const assistant = findAssistant(assistantId)
    if (assistant && assistant.status === 'streaming') {
      assistant.status = 'done'
    }
  } catch (err) {
    const assistant = findAssistant(assistantId)
    if ((err as Error).name === 'AbortError') {
      if (assistant) {
        assistant.status = 'done'
        if (!assistant.content) assistant.content = '_已停止生成。_'
      }
    } else {
      if (assistant) {
        assistant.status = 'error'
        assistant.content += `\n\n> 会话中断：${err instanceof Error ? err.message : '未知错误'}\n\n请确认后端服务已启动后重试。`
      }
      toast.push(err instanceof Error ? err.message : 'Agent 请求失败', 'error')
    }
  } finally {
    streaming.value = false
    controller = null
    currentStatus.value = ''
  }
}

function stop() {
  controller?.abort()
  streaming.value = false
  currentStatus.value = ''
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

function chooseFile() {
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    toast.push('仅支持 JPG、PNG、WebP 图片', 'error')
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    toast.push('图片大小不能超过 8 MB', 'error')
    return
  }
  uploading.value = true
  try {
    const result = await api.uploadImage(file)
    imageId.value = result.image_id
    imagePreview.value = result.thumbnail_url
    toast.push('图片已安全上传，可随消息交给 Agent 分析', 'success')
  } catch (err) {
    toast.push(err instanceof Error ? err.message : '图片上传失败', 'error')
  } finally {
    uploading.value = false
  }
}

function clearImage() {
  imageId.value = null
  imagePreview.value = ''
}

const configuredLLM = computed(() => app.meta?.mode.llm === 'deepseek')

onMounted(async () => {
  await app.load()
  await loadConversations()
  sessionMode.value = app.meta?.mode.llm === 'deepseek' ? 'deepseek' : 'local'
  const conversation = route.query.conversation
  if (typeof conversation === 'string' && conversation) {
    await loadConversation(conversation)
  }
  const image = route.query.image
  if (typeof image === 'string' && image) {
    imageId.value = image
    imagePreview.value = analysisStore.vision?.image_id === image
      ? analysisStore.vision.image_url
      : `/api/vision/images/${image}`
  }
  nextTick(() => textarea.value?.focus())
})

function toolDescription(name: string): string {
  const fallback: Record<string, string> = {
    predict_house_price: 'XGBoost 估值与 80% 参考区间',
    explain_house_price: 'TreeSHAP 价格归因与反事实',
    analyze_market: '邮编市场、趋势与稀缺属性',
    calculate_investment: 'NOI、DSCR、现金流与 IRR',
    search_property_knowledge: '混合检索知识库并返回引用',
    analyze_house_image: '读取已上传图片的分析结果',
  }
  return (app.meta as Meta | null)?.tools.find((tool) => tool.name === name)?.description ?? fallback[name] ?? '业务工具'
}
</script>

<template>
  <div class="page agent-page">
    <PageHeader
      eyebrow="AGENT WORKSPACE / 04"
      title="把问题交给一个<em>会用工具</em>的 Agent。"
      :lede="configuredLLM
        ? 'DeepSeek 负责理解与规划，六个确定性工具负责估值、解释、市场、投资、知识与图像。每一步工具调用都实时展示。'
        : '当前未配置 DeepSeek 密钥，Agent 运行在透明本地规划模式：同样的 SSE 事件流、同样的六个真实工具，不假装成大模型。'"
    >
      <template #actions>
        <button class="btn btn-ghost" @click="mobileHistory = true"><History :size="14" /> 历史会话</button>
        <button class="btn btn-primary" @click="newChat"><MessageSquarePlus :size="14" /> 新对话</button>
      </template>
    </PageHeader>

    <div class="agent-shell">
      <aside class="conversation-panel" :class="{ open: mobileHistory }">
        <div class="panel-top">
          <span class="panel-label">RECENT THREADS</span>
          <button class="icon-btn panel-close" aria-label="关闭历史" @click="mobileHistory = false"><X :size="16" /></button>
        </div>
        <button class="new-thread" @click="newChat">
          <MessageSquarePlus :size="14" />
          新建分析会话
        </button>
        <div class="conversation-list">
          <button
            v-for="item in conversations"
            :key="item.id"
            class="conversation-item"
            :class="{ active: item.id === conversationId }"
            @click="loadConversation(item.id)"
          >
            <span class="conv-title">{{ item.title }}</span>
            <span class="conv-meta">{{ dateCN(item.updated_at) }} · {{ item.mode === 'deepseek' ? 'DeepSeek' : '本地' }}</span>
          </button>
          <div v-if="!conversations.length" class="conversation-empty">
            还没有历史会话。<br />从一个真实问题开始。
          </div>
          <div v-if="loadingHistory" class="history-loading"><span class="spinner" /> 载入会话</div>
        </div>
        <div class="panel-foot">
          <div class="storage-note"><ShieldCheck :size="12" /> 会话存储于本地 SQLite</div>
          <div class="storage-sub">服务端持久化 · 刷新不丢失</div>
        </div>
      </aside>

      <section class="chat-shell">
        <header class="chat-head">
          <div class="advisor">
            <div class="advisor-avatar"><span>HM</span></div>
            <div class="advisor-copy">
              <div class="advisor-name">HouseMind Advisor <span class="advisor-verified">AI</span></div>
              <div class="advisor-status"><i :class="{ live: configuredLLM }" />{{ modeLabel }} · {{ modeDescription }}</div>
            </div>
          </div>
          <div class="chat-head-actions">
            <span class="badge" :class="configuredLLM ? 'badge-sage' : 'badge-gold'">{{ configuredLLM ? 'LLM CONNECTED' : 'LOCAL PLANNER' }}</span>
            <RouterLink to="/knowledge" class="head-link">知识库 <ChevronRight :size="12" /></RouterLink>
          </div>
        </header>

        <div ref="messageList" class="message-list">
          <div v-if="!messages.length" class="agent-empty">
            <div class="empty-emblem">
              <div class="emblem-ring" />
              <div class="emblem-core"><Sparkles :size="22" /></div>
              <span class="emblem-orbit one" /><span class="emblem-orbit two" />
            </div>
            <div class="empty-kicker">DECISION INTELLIGENCE, NOT A CHATBOT</div>
            <h2>今天想弄清楚<em>哪套房子</em>？</h2>
            <p>描述预算、邮编、面积或投资假设。Agent 会自主选择估值、解释、市场、投资、知识检索与图像工具，并把每一步摊开给你看。</p>
            <div class="prompt-grid">
              <button v-for="card in promptCards" :key="card.title" class="prompt-card" @click="send(card.prompt)">
                <div class="prompt-icon"><component :is="card.icon" :size="17" /></div>
                <div class="prompt-copy">
                  <span class="prompt-kicker">{{ card.kicker }}</span>
                  <strong>{{ card.title }}</strong>
                </div>
                <ArrowUp :size="14" class="prompt-arrow" />
              </button>
            </div>
            <div class="empty-foot">
              <Wrench :size="12" /> 6 个真实工具 · 实时 SSE 事件 · 每条结论可追溯到工具结果
            </div>
          </div>

          <template v-for="message in messages" :key="message.id">
            <div v-if="message.role === 'user'" class="message user-message">
              <div class="user-body">
                <div class="message-meta user-meta">
                  <span>YOU</span><span>{{ timeCN(message.createdAt) }}</span>
                </div>
                <div class="user-bubble">
                  <img v-if="message.imagePreview" :src="message.imagePreview" alt="用户上传的房屋图片" class="user-image" />
                  <p>{{ message.content }}</p>
                </div>
              </div>
            </div>

            <div v-else class="message assistant-message">
              <div class="assistant-avatar"><span>HM</span></div>
              <div class="assistant-body">
                <div class="message-meta">
                  <span>HOUSEMIND ADVISOR</span>
                  <span v-if="message.mode" class="meta-mode">{{ message.mode === 'deepseek' ? 'DEEPSEEK' : 'LOCAL' }}</span>
                  <span>{{ timeCN(message.createdAt) }}</span>
                </div>

                <div v-if="message.toolCalls?.length" class="trace-wrap">
                  <AgentToolTrace :calls="message.toolCalls" />
                </div>

                <div v-if="message.content" class="answer-card">
                  <MarkdownRenderer :content="message.content" />
                  <span v-if="message.status === 'streaming'" class="typing-cursor" />
                </div>

                <div v-if="message.status === 'streaming' && !message.content && !message.toolCalls?.length" class="thinking">
                  <span class="thinking-dots"><i /><i /><i /></span>
                  <span>{{ currentStatus || '正在理解你的问题' }}</span>
                </div>

                <div v-else-if="message.status === 'streaming' && !message.content && message.toolCalls?.length" class="thinking small">
                  <span class="spinner" />
                  <span>{{ currentStatus || '正在综合工具结果' }}</span>
                </div>

                <div v-if="message.citations?.length" class="citations">
                  <div class="citations-head"><BookOpen :size="12" /> 引用来源 <span>{{ message.citations.length }}</span></div>
                  <a
                    v-for="citation in message.citations"
                    :key="citation.index"
                    class="citation"
                    :href="citation.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span class="citation-index">{{ citation.index }}</span>
                    <span class="citation-copy"><strong>{{ citation.title }}</strong><small>{{ citation.section }} · {{ citation.source_name }}</small></span>
                    <ChevronRight :size="12" />
                  </a>
                </div>

                <div v-if="message.status === 'error'" class="answer-error"><X :size="12" /> 本轮回答未完整生成</div>
              </div>
            </div>
          </template>

          <div v-if="suggestions.length && !streaming" class="followups">
            <span class="followups-label">继续追问</span>
            <button v-for="suggestion in suggestions" :key="suggestion" @click="send(suggestion)">
              {{ suggestion }} <ArrowUp :size="11" />
            </button>
          </div>
        </div>

        <div class="composer-zone">
          <div v-if="imagePreview" class="attachment-preview">
            <img :src="imagePreview" alt="待发送的房屋图片" />
            <div>
              <strong>图片已就绪</strong>
              <small>Agent 会调用图像分析工具，仅描述可见特征</small>
            </div>
            <button aria-label="移除图片" @click="clearImage"><X :size="14" /></button>
          </div>
          <div class="composer" :class="{ busy: streaming }">
            <textarea
              ref="textarea"
              v-model="composer"
              rows="1"
              :placeholder="streaming ? 'Agent 正在回答…' : '描述一套房、一个投资假设，或一个房产概念…'"
              :disabled="streaming"
              aria-label="输入问题"
              @keydown="onKeydown"
            />
            <div class="composer-bar">
              <div class="composer-left">
                <button class="composer-icon" type="button" title="上传房屋图片" :disabled="uploading || streaming" @click="chooseFile">
                  <span v-if="uploading" class="spinner" />
                  <ImagePlus v-else :size="16" />
                </button>
                <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" class="sr-only" @change="onFileChange" />
                <span class="composer-hint">Enter 发送 · Shift + Enter 换行</span>
              </div>
              <div class="composer-right">
                <button v-if="streaming" class="send-btn stop" title="停止生成" @click="stop"><Square :size="12" /></button>
                <button v-else class="send-btn" title="发送" :disabled="(!composer.trim() && !imageId) || uploading" @click="send()">
                  <Send :size="14" />
                </button>
              </div>
            </div>
          </div>
          <div class="composer-legal">
            <ShieldCheck :size="10" />
            <span>输入经提示词注入检测；请勿上传身份证、合同或包含人脸的私密照片。</span>
            <span class="composer-mode">{{ configuredLLM ? 'DeepSeek 在线' : '本地模式 · 无外部 LLM 调用' }}</span>
          </div>
        </div>
      </section>

      <aside class="context-panel">
        <div class="context-block">
          <div class="context-label">THIS SESSION</div>
          <div class="session-mode">
            <div class="mode-orb"><Bot :size="16" /></div>
            <div><strong>{{ modeLabel }}</strong><small>{{ configuredLLM ? 'Function Calling' : 'Deterministic planner' }}</small></div>
          </div>
          <div class="session-stats">
            <div><span>工具调用</span><strong>{{ activeTools }}</strong></div>
            <div><span>引用来源</span><strong>{{ activeCitations }}</strong></div>
            <div><span>会话轮次</span><strong>{{ messages.filter((m) => m.role === 'user').length }}</strong></div>
          </div>
        </div>

        <div class="context-block">
          <div class="context-label">TOOLBELT / {{ tools.length || 6 }}</div>
          <div class="tool-list">
            <div v-for="tool in tools" :key="tool.name" class="tool-row">
              <div class="tool-row-icon"><component :is="toolIcon(tool.name)" :size="13" /></div>
              <div><strong>{{ tool.label }}</strong><small>{{ toolDescription(tool.name) }}</small></div>
            </div>
            <template v-if="!tools.length">
              <div v-for="name in Object.keys(toolIconMap)" :key="name" class="tool-row">
                <div class="tool-row-icon"><component :is="toolIcon(name)" :size="13" /></div>
                <div><strong>{{ name }}</strong><small>{{ toolDescription(name) }}</small></div>
              </div>
            </template>
          </div>
        </div>

        <div class="context-block guard-block">
          <div class="context-label">GUARDRAILS</div>
          <div class="guard-row"><ShieldCheck :size="12" /><span>提示词注入与越权检测</span></div>
          <div class="guard-row"><ShieldCheck :size="12" /><span>输出清洗与 PII 脱敏</span></div>
          <div class="guard-row"><ShieldCheck :size="12" /><span>30 次 / 分钟速率限制</span></div>
          <p>Agent 不替代房屋检查、法律意见或正式评估。</p>
        </div>
      </aside>
    </div>
    <div v-if="mobileHistory" class="mobile-scrim" @click="mobileHistory = false" />
  </div>
</template>

<style scoped>
.agent-page .page-head { padding-bottom: 18px; margin-bottom: 17px; }
.agent-shell { display: grid; grid-template-columns: 205px minmax(0, 1fr) 238px; gap: 13px; height: clamp(580px, calc(100vh - 267px), 850px); }
.conversation-panel, .context-panel, .chat-shell { border: 1px solid var(--line); background: rgba(251,248,241,.65); border-radius: 5px; min-height: 0; }
.conversation-panel { display: flex; flex-direction: column; padding: 15px 11px 11px; }
.panel-top { display: flex; justify-content: space-between; align-items: center; padding: 0 3px 9px; }
.panel-label { font-size: 7px; letter-spacing: .18em; color: var(--muted); }
.panel-close { display: none; }
.new-thread { display: flex; align-items: center; justify-content: center; gap: 6px; height: 33px; border: 1px solid var(--ink); background: var(--ink); color: var(--paper); border-radius: 3px; font-size: 9px; font-weight: 600; transition: background .2s; }
.new-thread:hover { background: #1c3a30; }
.conversation-list { flex: 1; overflow-y: auto; margin: 10px -3px 0; padding: 0 3px; display: flex; flex-direction: column; gap: 1px; }
.conversation-item { display: flex; flex-direction: column; gap: 3px; border: 0; background: transparent; text-align: left; padding: 8px 7px; border-radius: 3px; border-left: 2px solid transparent; }
.conversation-item:hover { background: rgba(16,35,29,.04); }
.conversation-item.active { background: rgba(176,138,82,.1); border-left-color: var(--gold); }
.conv-title { font-size: 8.5px; line-height: 1.4; font-weight: 550; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.conv-meta { font-size: 7px; color: var(--muted-light); }
.conversation-empty { padding: 16px 7px; font-size: 8.5px; line-height: 1.7; color: var(--muted); }
.history-loading { display: flex; align-items: center; gap: 6px; padding: 9px; font-size: 8px; color: var(--muted); }
.panel-foot { border-top: 1px solid var(--line-soft); padding: 9px 3px 0; margin-top: 8px; }
.storage-note { display: flex; align-items: center; gap: 4px; font-size: 7px; color: var(--muted); }
.storage-note svg { color: var(--sage); }
.storage-sub { font-size: 6.5px; color: var(--muted-light); margin-top: 2px; padding-left: 16px; }

.chat-shell { display: flex; flex-direction: column; overflow: hidden; background: rgba(251,248,241,.78); }
.chat-head { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 12px 17px; border-bottom: 1px solid var(--line); flex: 0 0 auto; }
.advisor { display: flex; align-items: center; gap: 9px; min-width: 0; }
.advisor-avatar, .assistant-avatar { width: 31px; height: 31px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; font-family: var(--font-serif); font-size: 10px; letter-spacing: .04em; flex: 0 0 auto; }
.advisor-name { font-size: 10px; font-weight: 680; letter-spacing: .02em; display: flex; align-items: center; gap: 5px; }
.advisor-verified { font-size: 6px; background: var(--gold); color: #fff; padding: 1px 3px; border-radius: 2px; }
.advisor-status { display: flex; align-items: center; gap: 4px; font-size: 7.5px; color: var(--muted); margin-top: 2px; }
.advisor-status i { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); }
.advisor-status i.live { background: var(--positive); }
.chat-head-actions { display: flex; align-items: center; gap: 9px; }
.head-link { display: inline-flex; align-items: center; gap: 2px; font-size: 8px; color: var(--muted); text-decoration: none; }
.head-link:hover { color: var(--ink); }

.message-list { flex: 1; overflow-y: auto; padding: 20px 22px 9px; scroll-behavior: smooth; }
.message { display: flex; gap: 9px; margin-bottom: 21px; }
.user-message { justify-content: flex-end; }
.user-body { max-width: 78%; display: flex; flex-direction: column; align-items: flex-end; }
.message-meta { display: flex; align-items: center; gap: 7px; font-size: 6.5px; letter-spacing: .12em; color: var(--muted-light); margin-bottom: 5px; }
.user-meta { justify-content: flex-end; }
.meta-mode { color: var(--gold); }
.user-bubble { background: var(--ink); color: var(--paper); padding: 10px 14px; border-radius: 10px 2px 10px 10px; }
.user-bubble p { font-size: 11.5px; line-height: 1.7; white-space: pre-wrap; }
.user-image { max-width: 260px; max-height: 180px; display: block; border-radius: 4px; margin-bottom: 8px; object-fit: cover; }
.assistant-message { align-items: flex-start; }
.assistant-avatar { margin-top: 2px; width: 27px; height: 27px; font-size: 8.5px; }
.assistant-body { min-width: 0; flex: 1; max-width: 810px; }
.answer-card { background: rgba(251,248,241,.85); border: 1px solid var(--line); border-radius: 2px 9px 9px 9px; padding: 14px 16px; box-shadow: 0 1px 0 rgba(255,255,255,.7) inset; }
.typing-cursor { display: inline-block; width: 5px; height: 13px; background: var(--gold); vertical-align: text-bottom; margin-left: 2px; animation: blink 0.9s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }
.thinking { display: flex; align-items: center; gap: 8px; padding: 12px 14px; border: 1px solid var(--line); background: rgba(251,248,241,.7); border-radius: 2px 9px 9px 9px; font-size: 8.5px; color: var(--muted); }
.thinking.small { border: 0; background: transparent; padding: 5px 2px; }
.thinking-dots { display: inline-flex; gap: 3px; }
.thinking-dots i { width: 4px; height: 4px; border-radius: 50%; background: var(--gold); animation: bounce 1.1s infinite; }
.thinking-dots i:nth-child(2) { animation-delay: .15s; }
.thinking-dots i:nth-child(3) { animation-delay: .3s; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: .45; } 30% { transform: translateY(-3px); opacity: 1; } }
.trace-wrap { max-width: 720px; }
.answer-error { display: flex; align-items: center; gap: 4px; margin-top: 7px; font-size: 8px; color: var(--negative); }

.citations { margin-top: 9px; border-top: 1px solid var(--line-soft); padding-top: 8px; }
.citations-head { display: flex; align-items: center; gap: 5px; font-size: 7.5px; letter-spacing: .08em; color: var(--muted); margin-bottom: 4px; }
.citations-head span { border: 1px solid var(--line); padding: 0 4px; border-radius: 6px; font-size: 6.5px; }
.citation { display: flex; align-items: center; gap: 7px; padding: 5px 2px; text-decoration: none; border-bottom: 1px solid rgba(16,35,29,.04); }
.citation:last-child { border-bottom: 0; }
.citation:hover .citation-copy strong { color: var(--gold); }
.citation-index { width: 15px; height: 15px; border: 1px solid var(--line); border-radius: 50%; display: grid; place-items: center; font-size: 6.5px; color: var(--muted); flex: 0 0 auto; }
.citation-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.citation-copy strong { font-size: 8px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.citation-copy small { font-size: 6.5px; color: var(--muted-light); }
.citation > svg { color: var(--muted-light); }

.agent-empty { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 12px 20px 10px; }
.empty-emblem { position: relative; width: 70px; height: 70px; display: grid; place-items: center; margin-bottom: 15px; }
.emblem-ring { position: absolute; inset: 0; border: 1px solid var(--line); border-radius: 50%; }
.emblem-core { width: 41px; height: 41px; background: var(--ink); color: var(--gold-light); border-radius: 50%; display: grid; place-items: center; }
.emblem-orbit { position: absolute; width: 3px; height: 3px; border-radius: 50%; background: var(--gold); }
.emblem-orbit.one { top: 10px; right: 12px; }
.emblem-orbit.two { bottom: 12px; left: 9px; background: var(--sage); }
.empty-kicker { font-size: 7px; letter-spacing: .18em; color: var(--gold); }
.agent-empty h2 { font-family: var(--font-serif); font-size: 29px; font-weight: 450; letter-spacing: -.03em; margin-top: 8px; }
.agent-empty h2 em { color: var(--gold); font-weight: 380; }
.agent-empty > p { max-width: 530px; font-size: 9.5px; line-height: 1.75; color: var(--muted); margin-top: 7px; }
.prompt-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; width: 100%; max-width: 600px; margin-top: 18px; }
.prompt-card { display: flex; align-items: center; gap: 9px; text-align: left; border: 1px solid var(--line); background: rgba(251,248,241,.62); border-radius: 3px; padding: 10px; transition: border-color .2s, background .2s, transform .2s; }
.prompt-card:hover { border-color: var(--gold); background: var(--paper-2); transform: translateY(-1px); }
.prompt-icon { width: 28px; height: 28px; border-radius: 3px; background: rgba(176,138,82,.09); color: var(--gold); display: grid; place-items: center; flex: 0 0 auto; }
.prompt-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.prompt-kicker { font-size: 6px; letter-spacing: .14em; color: var(--muted-light); }
.prompt-copy strong { font-size: 8.5px; font-weight: 600; line-height: 1.45; }
.prompt-arrow { margin-left: auto; color: var(--muted-light); transform: rotate(45deg); flex: 0 0 auto; }
.empty-foot { display: flex; align-items: center; gap: 5px; margin-top: 17px; font-size: 7px; color: var(--muted-light); }

.followups { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding: 0 0 10px 36px; }
.followups-label { font-size: 7px; letter-spacing: .1em; color: var(--muted-light); width: 100%; margin-bottom: 1px; }
.followups button { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--line); background: transparent; border-radius: 99px; padding: 5px 9px; font-size: 7.5px; color: var(--muted); }
.followups button:hover { border-color: var(--gold); color: var(--ink); }
.followups button svg { transform: rotate(45deg); }

.composer-zone { flex: 0 0 auto; padding: 6px 15px 10px; border-top: 1px solid var(--line-soft); background: rgba(251,248,241,.88); }
.attachment-preview { display: flex; align-items: center; gap: 8px; border: 1px solid var(--line); background: var(--paper-2); padding: 6px; border-radius: 3px; margin-bottom: 6px; }
.attachment-preview img { width: 36px; height: 30px; object-fit: cover; border-radius: 2px; }
.attachment-preview div { display: flex; flex-direction: column; flex: 1; gap: 1px; }
.attachment-preview strong { font-size: 8px; }
.attachment-preview small { font-size: 7px; color: var(--muted); }
.attachment-preview button { border: 0; background: transparent; color: var(--muted); }
.composer { border: 1px solid var(--line); border-radius: 4px; background: var(--paper-2); padding: 8px 9px 6px; transition: border-color .2s, box-shadow .2s; }
.composer:focus-within { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(176,138,82,.08); }
.composer.busy { background: rgba(234,226,212,.3); }
.composer textarea { width: 100%; border: 0; outline: 0; background: transparent; resize: none; min-height: 23px; height: 23px; max-height: 118px; font-size: 11px; line-height: 1.65; padding: 1px 2px; }
.composer textarea::placeholder { color: var(--muted-light); }
.composer-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 2px; }
.composer-left { display: flex; align-items: center; gap: 8px; }
.composer-icon { border: 0; background: transparent; color: var(--muted); width: 25px; height: 25px; display: grid; place-items: center; border-radius: 3px; }
.composer-icon:hover { background: rgba(16,35,29,.05); color: var(--ink); }
.composer-hint { font-size: 6.5px; color: var(--muted-light); }
.send-btn { width: 27px; height: 27px; border-radius: 3px; background: var(--ink); color: var(--paper); display: grid; place-items: center; }
.send-btn:disabled { opacity: .35; cursor: not-allowed; }
.send-btn.stop { background: var(--clay); }
.composer-legal { display: flex; align-items: center; gap: 4px; margin-top: 5px; font-size: 6.5px; color: var(--muted-light); }
.composer-legal svg { color: var(--sage); flex: 0 0 auto; }
.composer-mode { margin-left: auto; white-space: nowrap; }

.context-panel { padding: 14px 12px; overflow-y: auto; }
.context-block { padding-bottom: 14px; margin-bottom: 14px; border-bottom: 1px solid var(--line-soft); }
.context-block:last-child { border-bottom: 0; margin-bottom: 0; padding-bottom: 0; }
.context-label { font-size: 6.5px; letter-spacing: .16em; color: var(--muted); margin-bottom: 9px; }
.session-mode { display: flex; align-items: center; gap: 8px; }
.mode-orb { width: 30px; height: 30px; border-radius: 50%; background: var(--ink); color: var(--gold-light); display: grid; place-items: center; flex: 0 0 auto; }
.session-mode div:last-child { display: flex; flex-direction: column; gap: 1px; }
.session-mode strong { font-size: 8.5px; font-weight: 650; }
.session-mode small { font-size: 7px; color: var(--muted-light); }
.session-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-top: 11px; }
.session-stats div { display: flex; flex-direction: column; gap: 1px; }
.session-stats span { font-size: 6.5px; color: var(--muted); }
.session-stats strong { font-family: var(--font-serif); font-size: 17px; font-weight: 480; }
.tool-list { display: flex; flex-direction: column; gap: 9px; }
.tool-row { display: flex; gap: 7px; align-items: flex-start; }
.tool-row-icon { width: 21px; height: 21px; border: 1px solid var(--line); border-radius: 3px; display: grid; place-items: center; color: var(--gold); flex: 0 0 auto; }
.tool-row div:last-child { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.tool-row strong { font-size: 7.5px; font-weight: 650; }
.tool-row small { font-size: 6.5px; line-height: 1.45; color: var(--muted-light); }
.guard-row { display: flex; align-items: center; gap: 5px; font-size: 7px; color: var(--muted); padding: 3px 0; }
.guard-row svg { color: var(--sage); flex: 0 0 auto; }
.guard-block p { margin-top: 7px; font-size: 6.5px; line-height: 1.6; color: var(--muted-light); padding-top: 7px; border-top: 1px solid var(--line-soft); }
.mobile-scrim { display: none; }

@media (max-width: 1380px) {
  .agent-shell { grid-template-columns: 195px minmax(0, 1fr) 218px; }
  .context-panel { padding: 13px 10px; }
}
@media (max-width: 1240px) {
  .agent-shell { grid-template-columns: 195px minmax(0, 1fr); }
  .context-panel { display: none; }
}
@media (max-width: 900px) {
  .agent-shell { grid-template-columns: 1fr; height: clamp(570px, calc(100vh - 240px), 780px); }
  .conversation-panel { display: none; position: fixed; left: 12px; top: 82px; bottom: 18px; width: 260px; z-index: 70; box-shadow: 0 24px 60px rgba(16,35,29,.22); background: var(--paper-2); }
  .conversation-panel.open { display: flex; }
  .panel-close { display: inline-flex; }
  .mobile-scrim { display: block; position: fixed; inset: 0; z-index: 65; background: rgba(6,18,14,.35); }
  .chat-head { padding: 10px 13px; }
  .chat-head-actions .badge { display: none; }
  .message-list { padding: 16px 13px 7px; }
  .user-body { max-width: 88%; }
  .composer-zone { padding: 5px 10px 8px; }
  .composer-legal span:nth-child(2) { display: none; }
  .agent-empty { padding: 7px 4px; }
  .agent-empty h2 { font-size: 25px; }
  .prompt-grid { grid-template-columns: 1fr; max-width: 400px; }
  .followups { padding-left: 0; }
}
@media (max-width: 520px) {
  .advisor-status { max-width: 210px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .head-link { display: none; }
  .assistant-avatar { width: 23px; height: 23px; font-size: 7px; }
  .message { gap: 7px; }
  .answer-card { padding: 11px 12px; }
  .composer-hint { display: none; }
}
</style>
