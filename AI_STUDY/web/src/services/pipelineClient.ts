type RiskInput = {
  averageScore: number
  attendanceRate: number
  classQualityScore: number
  schoolEnvironmentScore: number
}

type ScheduleInput = {
  koreanLevel: number
  mathLevel: number
  englishLevel: number
  fatigue: number
  studyHours: number
}

type TwinInput = {
  currentAverage: number
  planQuality: number
  consistency: number
  weeks: number
}

type CausalInput = {
  attendanceImpact: number
  classQualityImpact: number
  selfStudyImpact: number
  environmentImpact: number
}

type XaiInput = {
  attendance: number
  understanding: number
  fatigue: number
  classQuality: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function analyzeClassFromText(transcript: string) {
  const res = await fetch(`${API_BASE}/api/analysis/class-from-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function runFullPipeline(input: {
  transcript: string
  risk_input: RiskInput
  schedule_input: ScheduleInput
  twin_input: TwinInput
  causal_input: CausalInput
  xai_input: XaiInput
}) {
  const res = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchPublicSummary() {
  const res = await fetch(`${API_BASE}/api/public/summary`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchPublicSummaryBySchool(atptCode: string, schoolCode: string) {
  const q = new URLSearchParams({ atpt_code: atptCode, school_code: schoolCode })
  const res = await fetch(`${API_BASE}/api/public/summary?${q.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function searchSchools(query: string, atptCode?: string) {
  const q = new URLSearchParams({ query })
  if (atptCode?.trim()) q.set('atpt_code', atptCode.trim())
  const res = await fetch(`${API_BASE}/api/public/schools?${q.toString()}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 160)}`)
  }
  return res.json()
}

export async function fetchTimetable(
  atptCode: string,
  schoolCode: string,
  grade = 1,
  cls = 1,
) {
  const q = new URLSearchParams({
    atpt_code: atptCode,
    school_code: schoolCode,
    grade: String(grade),
    cls: String(cls),
  })
  const res = await fetch(`${API_BASE}/api/public/timetable?${q.toString()}`)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 160)}`)
  }
  return res.json()
}

export async function fetchKessStats(input: { region?: string; year?: number; grade?: number }) {
  const res = await fetch(`${API_BASE}/api/public/kess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function fetchAlimiEnvironment(input: {
  atpt_code?: string
  school_code?: string
  school_name?: string
}) {
  const res = await fetch(`${API_BASE}/api/public/alimi`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function predictRiskSklearn(input: {
  averageScore: number
  attendanceRate: number
  classQualityScore: number
  schoolEnvironmentScore: number
}) {
  const res = await fetch(`${API_BASE}/api/models/risk/predict-sklearn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function optimizeScheduleSb3(input: {
  koreanLevel: number
  mathLevel: number
  englishLevel: number
  fatigue: number
  studyHours: number
  objective?: string
}) {
  const res = await fetch(`${API_BASE}/api/rl/schedule/optimize-sb3`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function explainShap(input: {
  averageScore: number
  attendanceRate: number
  classQualityScore: number
  schoolEnvironmentScore: number
}) {
  const res = await fetch(`${API_BASE}/api/xai/shap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

// ─────────────────────────────────────────────────
// 확장 기능 클라이언트 (제안서 기반)
// ─────────────────────────────────────────────────

export type SubjectScore = {
  subject: string
  score: number
  importance?: number
}

export async function recommendPathway(input: {
  grade?: number
  subjects?: SubjectScore[]
  goal?: string
  studyHoursPerDay?: number
}) {
  const res = await fetch(`${API_BASE}/api/pathway/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function checkWarning(input: {
  recentScores?: number[]
  attendanceRate: number
  submissionRate?: number
  engagementScore?: number
}) {
  const res = await fetch(`${API_BASE}/api/warning/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function fetchEquityIndex(input: {
  region?: string
  schoolType?: string
  year?: number
}) {
  const res = await fetch(`${API_BASE}/api/equity/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function matchResources(input: {
  subject: string
  level?: number
  grade?: number
  formatPref?: string
}) {
  const res = await fetch(`${API_BASE}/api/resources/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function nlqQuery(input: {
  query: string
  context?: string
}) {
  const res = await fetch(`${API_BASE}/api/nlq/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }
  return res.json()
}
