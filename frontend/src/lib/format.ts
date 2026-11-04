export const usd = (value: number | null | undefined, compact = false): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (compact) {
    if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`
    if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}k`
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export const num = (value: number | null | undefined, digits = 0): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: digits }).format(value)
}

export const pct = (value: number | null | undefined, digits = 1): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toFixed(digits)}%`
}

export const signedUsd = (value: number): string => `${value >= 0 ? '+' : '−'}${usd(Math.abs(value))}`

export const dateCN = (value?: string): string => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(date)
}

export const timeCN = (value?: string): string => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(date)
}

export const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value))
