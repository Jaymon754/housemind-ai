import { BASE } from './client'
import type { AgentToolCall, Citation } from '@/types'

export interface AgentStreamHandlers {
  onMeta?: (data: { conversation_id: string; mode: string; guard: { severity: string; reasons: string[] } }) => void
  onStatus?: (data: { stage: string; label: string }) => void
  onToolCall?: (data: { name: string; label: string; arguments: Record<string, unknown>; reason: string }) => void
  onToolResult?: (data: { name: string; label: string; summary: string; latency_ms: number; data: Record<string, unknown> }) => void
  onToolError?: (data: { name: string; message: string }) => void
  onToken?: (text: string) => void
  onCitations?: (citations: Citation[]) => void
  onDone?: (data: { message_id: string; conversation_id: string; mode: string; suggestions: string[] }) => void
}

const parseEvent = (block: string): { event: string; data: unknown } | null => {
  const lines = block.split('\n')
  let event = 'message'
  const dataLines: string[] = []
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  try {
    return { event, data: JSON.parse(dataLines.join('\n')) }
  } catch {
    return null
  }
}

export async function streamAgent(
  payload: { message: string; conversation_id?: string | null; image_id?: string | null },
  handlers: AgentStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE}/api/agent/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!response.ok) {
    let detail = `Agent 请求失败（${response.status}）`
    try {
      const data = await response.json()
      if (typeof data.detail === 'string') detail = data.detail
    } catch {
      /* noop */
    }
    throw new Error(detail)
  }
  if (!response.body) throw new Error('浏览器不支持流式响应')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const parsed = parseEvent(block)
      if (!parsed) continue
      const data = parsed.data as never
      switch (parsed.event) {
        case 'meta':
          handlers.onMeta?.(data)
          break
        case 'status':
          handlers.onStatus?.(data)
          break
        case 'tool_call':
          handlers.onToolCall?.(data)
          break
        case 'tool_result':
          handlers.onToolResult?.(data)
          break
        case 'tool_error':
          handlers.onToolError?.(data)
          break
        case 'token':
          handlers.onToken?.((data as { text: string }).text)
          break
        case 'citations':
          handlers.onCitations?.(data as Citation[])
          break
        case 'done':
          handlers.onDone?.(data)
          break
      }
    }
  }
}

export type { AgentToolCall }
