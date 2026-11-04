export interface ZipOption {
  zipcode: string
  region: string
  median_price: number
  count: number
  median_ppsf: number
}

export interface ToolDefinition {
  name: string
  label: string
  description: string
  parameters: Record<string, unknown>
}

export interface Meta {
  app: { name: string; version: string; tagline: string }
  mode: { llm: string; llm_label: string; vision: string; rag: string }
  dataset: { name: string; rows: number; period: { start: string; end: string }; currency: string; target: string }
  performance: {
    mae: number
    rmse: number
    r2: number
    mape: number
    interval_coverage: number
    baseline_lift: number
    best_model: string
  }
  zipcodes: ZipOption[]
  defaults: Record<string, number>
  ranges: Record<string, { p01: number; p99: number; min: number; max: number }>
  features: { key: string; label: string }[]
  tools: ToolDefinition[]
  suggested_questions: string[]
}

export interface Health {
  status: string
  app: string
  version: string
  uptime_seconds: number
  model: { loaded: boolean; name: string; mae: number; r2: number; rows: number }
  rag: { backend: string; documents: number; chunks: number }
  llm: { mode: string; model: string | null }
  vision: { mode: string; model: string }
}

export interface RegionStat {
  region: string
  count: number
  share_pct: number
  median_price: number
  mean_price: number
  median_ppsf: number
  median_area: number
}

export interface TrendPoint {
  month: string
  label: string
  count: number
  median_price: number
  median_ppsf: number
}

export interface MapPoint {
  lat: number
  lon: number
  price: number
  area: number
  region: string
}

export interface DashboardData {
  dataset: string
  period: { start: string; end: string }
  overview: {
    total_sales: number
    median_price: number
    average_price: number
    median_ppsf: number
    average_area: number
    median_area: number
    zipcodes: number
    waterfront_share_pct: number
    renovated_share_pct: number
  }
  market_pulse: {
    waterfront_median: number
    inland_median: number
    waterfront_premium_pct: number
    renovated_median: number
    not_renovated_median: number
    renovated_descriptive_gap_pct: number
    peak_month: string
    peak_median: number
    trough_month: string
    trough_median: number
    note: string
  }
  histogram: { bin: string; low: number; count: number }[]
  regions: RegionStat[]
  trend: TrendPoint[]
  conditions: { condition: number; label: string; count: number; median_price: number }[]
  grades: { grade: number; count: number; median_price: number }[]
  top_zipcodes: { zipcode: string; count: number; median_price: number; median_ppsf: number }[]
  map_points: MapPoint[]
  area_points: { area: number; price: number; bedrooms: number; grade: number; region: string }[]
  area_price_bands: { band: string; count: number; median_price: number; median_ppsf: number }[]
  quality: {
    raw_rows: number
    clean_rows: number
    duplicate_sale_ids_removed: number
    missing_values_after_clean: number
    cleaning_rules: string[]
  }
  generated_at: string
}

export interface Contribution {
  feature: string
  label: string
  value: number | string | boolean | null
  value_display: string
  amount: number
  direction: 'positive' | 'negative'
  share_pct: number
}

export interface Comparable {
  price: number
  sqft_living: number
  bedrooms: number
  bathrooms: number
  grade: number
  year_built: number
  zipcode: string
  region: string
  price_per_sqft: number
  sold_at: string
  distance_miles: number
  similarity: number
  same_zip: boolean
}

export interface Market {
  zipcode: string
  region: string
  sales_count: number
  monthly_sales: number
  median_price: number
  median_ppsf: number
  predicted_ppsf: number
  ppsf_percentile: number
  trend_pct_sample_period: number
  trend_note: string
}

export interface ValuationResult {
  input: Record<string, number | string | null>
  estimate: {
    value: number
    raw_value: number
    range_low: number
    range_high: number
    currency: string
    price_per_sqft: number
    interval_level: number
    generated_at: string
  }
  confidence: { score: number; label: string; basis: string[] }
  assessment: {
    asking_price: number
    difference: number
    difference_pct: number
    verdict: string
    tone: 'underpriced' | 'fair' | 'overpriced'
    message: string
  } | null
  market: Market
  comparables: Comparable[]
  explanation: {
    base_value: number
    prediction: number
    contributions: Contribution[]
    positive: Contribution[]
    negative: Contribution[]
    narrative: string
    method: string
    what_if: { label: string; delta: number; delta_pct: number }[]
  }
  warnings: string[]
  assumptions: string[]
  model: { name: string; version: string; mae: number; r2: number; trained_at: string; test_rows: number }
}

export interface InvestmentInputs {
  purchase_price: number
  down_payment_pct: number
  interest_rate: number
  loan_term_years: number
  monthly_rent: number
  vacancy_rate_pct: number
  property_tax_rate_pct: number
  insurance_annual: number
  hoa_monthly: number
  maintenance_pct: number
  closing_cost_pct: number
  rent_growth_pct: number
  appreciation_pct: number
  holding_years: number
}

export interface InvestmentResult {
  inputs: InvestmentInputs
  summary: {
    purchase_price: number
    down_payment: number
    closing_costs: number
    loan_amount: number
    total_cash_invested: number
    monthly_mortgage: number
    annual_debt_service: number
    effective_gross_income: number
    operating_expenses: number
    noi: number
    annual_cash_flow: number
    monthly_cash_flow: number
  }
  returns: {
    cap_rate_pct: number
    cash_on_cash_pct: number
    dscr: number | null
    break_even_occupancy_pct: number
    payback_years: number | null
    holding_years: number
    sale_price: number
    net_sale_proceeds: number
    total_profit: number
    total_roi_pct: number
    equity_multiple: number
    irr_pct: number | null
    annualized_roi_pct: number | null
  }
  monthly: {
    gross_rent: number
    vacancy_loss: number
    effective_rent: number
    property_tax: number
    insurance: number
    hoa: number
    maintenance: number
    mortgage: number
    net_cash_flow: number
  }
  schedule: {
    year: number
    rent_income: number
    operating_expenses: number
    noi: number
    debt_service: number
    cash_flow: number
    loan_balance: number
    cumulative_cash_flow: number
  }[]
  sensitivity: { rent: number; rate: number; monthly_cash_flow: number; cash_on_cash: number }[]
  warnings: string[]
  verdict: { label: string; tone: string; note: string }
  assumptions: string[]
  disclaimer: string
}

export interface ScenarioResponse {
  base: InvestmentResult
  custom: InvestmentResult
  optimistic: InvestmentResult
  pessimistic: InvestmentResult
  scenario_definitions: Record<string, string>
}

export interface KnowledgeResult {
  id: string
  doc_id: string
  title: string
  section: string
  category: string
  category_label: string
  content: string
  snippet: string
  source_name: string
  source_url: string
  updated: string
  score: number
}

export interface Citation {
  index: number
  title: string
  section: string
  source_name: string
  source_url: string
  category: string
  score: number
}

export interface KnowledgeAnswer {
  question: string
  answer: string
  citations: Citation[]
  results: KnowledgeResult[]
  mode: string
  retrieval: { backend: string; strategy: string; chunks: number; documents: number }
}

export interface KnowledgeStats {
  backend: string
  documents: number
  chunks: number
  categories: { key: string; label: string; count: number }[]
  embedding: string
  indexed_at: string
  documents_list: {
    doc_id: string
    title: string
    category: string
    category_label: string
    source_name: string
    source_url: string
    sections: number
  }[]
}

export interface UploadResult {
  image_id: string
  filename: string
  image_url: string
  thumbnail_url: string
  uploaded_at: string
  metadata_stripped: boolean
  size_kb: number
  features: VisionResult['features']
}

export interface VisionResult {
  image_id: string
  image_url: string
  thumbnail_url: string
  mode: string
  model: string
  size_kb?: number
  metadata_stripped?: boolean
  features: {
    width: number
    height: number
    aspect_ratio: number
    orientation: string
    brightness: number
    contrast: number
    saturation: number
    warmth: number
    temperature: string
    edge_density: number
    dominant_colors: { hex: string; share_pct: number }[]
    observations: string[]
    average_color: string
  }
  semantic: {
    room_type: string
    style: string
    style_confidence: number
    visible_materials: string[]
    observations: string[]
    strengths: string[]
    concerns: string[]
    confidence: number
    capability_note?: string
    questions_for_viewing?: string[]
    fallback_reason?: string
  }
  analyzed_at: string
  disclaimer: string
}

export interface AgentToolCall {
  id: string
  name: string
  label: string
  arguments: Record<string, unknown>
  reason: string
  status: 'running' | 'done' | 'error'
  summary?: string
  latency_ms?: number
  data?: Record<string, unknown>
  error?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode?: string
  createdAt?: string
  toolCalls?: AgentToolCall[]
  citations?: Citation[]
  status?: 'streaming' | 'done' | 'error'
  imagePreview?: string
}

export interface AgentConversation {
  id: string
  title: string
  mode: string
  updated_at: string
}
