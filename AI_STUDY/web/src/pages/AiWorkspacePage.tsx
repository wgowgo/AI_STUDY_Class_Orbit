import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type React from 'react'
import { askAi, type ChatMessage } from '../services/aiClient'
import {
  analyzeClassFromText,
  fetchPublicSummaryBySchool,
  fetchTimetable,
  fetchKessStats,
  fetchAlimiEnvironment,
  predictRiskSklearn,
  optimizeScheduleSb3,
  explainShap,
  runFullPipeline,
  searchSchools,
  recommendPathway,
  checkWarning,
  fetchEquityIndex,
  matchResources,
  nlqQuery,
  type SubjectScore,
} from '../services/pipelineClient'
import { transcribeAudio } from '../services/sttClient'
import { deriveClassInputFromTranscript } from '../features/ai/textAutoAnalyzer'
import {
  analyzeCausal,
  analyzeClass,
  explainPrediction,
  optimizeSchedule,
  predictRisk,
  simulateTwin,
} from '../features/ai/pipeline'

type Props = {
  onBack: () => void
}

type AiTab =
  | 'overview'
  | 'class-analysis'
  | 'risk'
  | 'schedule'
  | 'twin'
  | 'causal'
  | 'xai'
  | 'stack'
  | 'chat'
  | 'pathway'
  | 'warning'
  | 'equity'
  | 'resources'
  | 'nlq'

const TAB_LABELS: Record<AiTab, string> = {
  overview: 'Summary',
  'class-analysis': '수업 분석',
  risk: '격차 예측',
  schedule: '시간표',
  twin: '시뮬레이션',
  causal: '인과',
  xai: '설명',
  stack: '학교 데이터',
  chat: '대화',
  pathway: '학습 경로',
  warning: '조기 경보',
  equity: '형평성 지수',
  resources: '자원 매칭',
  nlq: '데이터 질의',
}

export function AiWorkspacePage({ onBack }: Props) {
  const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v))
  type SchoolLevel = 'high' | 'middle' | 'elementary' | 'all'
  const [tab, setTab] = useState<AiTab>('overview')
  const [navOpen, setNavOpen] = useState(false)
  const [apiStatus, setApiStatus] = useState<
    Record<
      | 'class_from_text'
      | 'pipeline_run'
      | 'stt'
      | 'neis_summary'
      | 'neis_timetable'
      | 'kess'
      | 'alimi'
      | 'sklearn'
      | 'sb3'
      | 'shap'
      | 'chat',
      'idle' | 'live' | 'local' | 'error'
    >
  >({
    class_from_text: 'idle',
    pipeline_run: 'idle',
    stt: 'idle',
    neis_summary: 'idle',
    neis_timetable: 'idle',
    kess: 'idle',
    alimi: 'idle',
    sklearn: 'idle',
    sb3: 'idle',
    shap: 'idle',
    chat: 'idle',
  })
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        '안녕하세요. 수업 분석, 격차 예측, 시간표 최적화 관련 질문을 입력하면 답변합니다.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const [classInput, setClassInput] = useState({
    transcriptLength: 1200,
    explanationFocus: 72,
    repetitionCount: 8,
    questionPromptRate: 58,
    keywordDensity: 61,
  })
  const [classDurationMinutes, setClassDurationMinutes] = useState(45)
  const [riskInput, setRiskInput] = useState({
    averageScore: 71,
    attendanceRate: 88,
    classQualityScore: 74,
    schoolEnvironmentScore: 67,
  })
  const [subjects, setSubjects] = useState<
    Array<{ id: string; name: string; score: number; importance: number }>
  >([
    { id: 'math', name: '수학', score: 62, importance: 1.2 },
    { id: 'eng', name: '영어', score: 71, importance: 1.0 },
    { id: 'kor', name: '국어', score: 74, importance: 1.0 },
    { id: 'sci', name: '과학', score: 66, importance: 0.95 },
    { id: 'soc', name: '사회', score: 73, importance: 0.9 },
  ])
  const [newSubjectName, setNewSubjectName] = useState('')
  const [scheduleInput, setScheduleInput] = useState({
    koreanLevel: 68,
    mathLevel: 56,
    englishLevel: 73,
    fatigue: 44,
    studyHours: 4.5,
  })
  const [twinInput, setTwinInput] = useState({
    currentAverage: 67,
    planQuality: 76,
    consistency: 63,
    weeks: 12,
  })
  const [causalInput, setCausalInput] = useState({
    attendanceImpact: 39,
    classQualityImpact: 31,
    selfStudyImpact: 22,
    environmentImpact: 8,
  })
  const [xaiInput, setXaiInput] = useState({
    attendance: 84,
    understanding: 61,
    fatigue: 48,
    classQuality: 73,
  })
  const [transcriptText, setTranscriptText] = useState(
    '오늘은 이차함수의 꼭짓점 형태를 정리합니다. 왜 이 공식이 필요한지 생각해봅시다. 이해가 안 되는 부분 있나요? 핵심 개념을 다시 정리해보겠습니다.',
  )
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [sttLoading, setSttLoading] = useState(false)
  const [sttError, setSttError] = useState<string | null>(null)
  const [analysisMeta, setAnalysisMeta] = useState({
    sentenceCount: 0,
    questionCount: 0,
    repeatedSentenceCount: 0,
  })
  const [publicSummary, setPublicSummary] = useState<string>('아직 조회하지 않음')
  const [schoolQuery, setSchoolQuery] = useState('')
  const [schoolLevel, setSchoolLevel] = useState<SchoolLevel>('high')
  const [schoolSearchLoading, setSchoolSearchLoading] = useState(false)
  const [schoolSearchError, setSchoolSearchError] = useState<string | null>(null)
  const [schoolResults, setSchoolResults] = useState<
    Array<{
      ATPT_OFCDC_SC_CODE: string
      ATPT_OFCDC_SC_NM: string
      SD_SCHUL_CODE: string
      SCHUL_NM: string
    }>
  >([])
  const [relatedChips, setRelatedChips] = useState<string[]>([])
  const [schoolSuggestOpen, setSchoolSuggestOpen] = useState(false)
  const [selectedSchool, setSelectedSchool] = useState<{
    atptCode: string
    schoolCode: string
    schoolName: string
  } | null>(null)
  const [timetableText, setTimetableText] = useState<string>('아직 조회하지 않음')
  const [stackDetailsOpen, setStackDetailsOpen] = useState(false)
  const [kessText, setKessText] = useState<string>('아직 조회하지 않음')
  const [alimiText, setAlimiText] = useState<string>('아직 조회하지 않음')
  const [modelText, setModelText] = useState<string>('아직 조회하지 않음')
  const [rlText, setRlText] = useState<string>('아직 조회하지 않음')
  const [shapText, setShapText] = useState<string>('아직 조회하지 않음')
  const [neisSummarySource, setNeisSummarySource] = useState('')
  const [timetableSource, setTimetableSource] = useState('')
  const [kessSource, setKessSource] = useState('')
  const [alimiSource, setAlimiSource] = useState('')
  const scenarioFileRef = useRef<HTMLInputElement>(null)
  const [scenarioImportError, setScenarioImportError] = useState<string | null>(null)

  // ── 확장 탭 state ──────────────────────────────
  // 학습 경로
  const [pathwaySubjects, setPathwaySubjects] = useState<SubjectScore[]>([
    { subject: '수학', score: 62, importance: 1.2 },
    { subject: '영어', score: 71, importance: 1.0 },
    { subject: '국어', score: 74, importance: 1.0 },
  ])
  const [pathwayGoal, setPathwayGoal] = useState('내신')
  const [pathwayHours, setPathwayHours] = useState(3.0)
  const [pathwayResult, setPathwayResult] = useState<Record<string, unknown> | null>(null)
  const [pathwayLoading, setPathwayLoading] = useState(false)
  const [pathwayError, setPathwayError] = useState<string | null>(null)

  // 조기 경보
  const [warningScores, setWarningScores] = useState([75, 70, 65])
  const [warningAttendance, setWarningAttendance] = useState(88)
  const [warningSubmission, setWarningSubmission] = useState(92)
  const [warningEngagement, setWarningEngagement] = useState(65)
  const [warningResult, setWarningResult] = useState<Record<string, unknown> | null>(null)
  const [warningLoading, setWarningLoading] = useState(false)
  const [warningError, setWarningError] = useState<string | null>(null)

  // 형평성 지수
  const [equityRegion, setEquityRegion] = useState('서울')
  const [equitySchoolType, setEquitySchoolType] = useState('고등')
  const [equityYear, setEquityYear] = useState(2025)
  const [equityResult, setEquityResult] = useState<Record<string, unknown> | null>(null)
  const [equityLoading, setEquityLoading] = useState(false)
  const [equityError, setEquityError] = useState<string | null>(null)

  // 자원 매칭
  const [resourceSubject, setResourceSubject] = useState('수학')
  const [resourceLevel, setResourceLevel] = useState(62)
  const [resourceFormat, setResourceFormat] = useState('')
  const [resourceResult, setResourceResult] = useState<Record<string, unknown> | null>(null)
  const [resourceLoading, setResourceLoading] = useState(false)
  const [resourceError, setResourceError] = useState<string | null>(null)

  // 자연어 질의
  const [nlqInput, setNlqInput] = useState('')
  const [nlqResult, setNlqResult] = useState<Record<string, unknown> | null>(null)
  const [nlqLoading, setNlqLoading] = useState(false)
  const [nlqError, setNlqError] = useState<string | null>(null)
  const [nlqHistory, setNlqHistory] = useState<Array<{ query: string; result: Record<string, unknown> }>>([])

  const canSend = input.trim().length > 0 && !loading
  const historyCount = useMemo(
    () => messages.filter((m) => m.role === 'user').length,
    [messages],
  )
  const classResult = useMemo(() => analyzeClass(classInput), [classInput])
  const riskResult = useMemo(() => predictRisk(riskInput), [riskInput])
  const scheduleResult = useMemo(() => optimizeSchedule(scheduleInput), [scheduleInput])
  const twinResult = useMemo(() => simulateTwin(twinInput), [twinInput])
  const causalResult = useMemo(() => analyzeCausal(causalInput), [causalInput])
  const xaiResult = useMemo(() => explainPrediction(xaiInput), [xaiInput])

  const HelpPanel = ({
    title,
    items,
  }: {
    title: string
    items: Array<{ term: string; meaning: string; tip?: string }>
  }) => (
    <aside className=ai-help aria-label={`${title} 도움말`}>
      <p className=ai-help-kicker>Guide</p>
      <h3 className=ai-help-title>{title}</h3>
      <dl className=ai-help-list>
        {items.map((it) => (
          <div key={it.term} className=ai-help-item>
            <dt className=ai-help-term>{it.term}</dt>
            <dd className=ai-help-meaning>{it.meaning}</dd>
            {it.tip ? <dd className=ai-help-tip>{it.tip}</dd> : null}
          </div>
        ))}
      </dl>
    </aside>
  )

  const CodeLines = ({
    title,
    lines,
  }: {
    title: string
    lines: Array<{
      key: string
      value: React.ReactNode
      unit?: string
      note?: string
      severity?: 'info' | 'warn' | 'error' | 'ok'
    }>
  }) => (
    <section className=ai-codepanel aria-label={title}>
      <header className=ai-codepanel-head>
        <span className=ai-codepanel-title>{title}</span>
      </header>
      <div className=ai-code>
        {lines.map((l, idx) => (
          <div key={`${l.key}-${idx}`} className={`ai-codeline ai-codeline--${l.severity ?? 'info'}`}>
            <span className=ai-lno>{String(idx + 1).padStart(2, '0')}</span>
            <span className=ai-key>{l.key}</span>
            <span className=ai-colon>:</span>
            <span className=ai-val>
              {l.value}
              {l.unit ? <span className=ai-unit> {l.unit}</span> : null}
            </span>
            {l.note ? <span className=ai-note> // {l.note}</span> : null}
          </div>
        ))}
      </div>
    </section>
  )

  const classifySentence = (s: string) => {
    const t = s.trim()
    if (!t) return 'other' as const
    const isQuestion = /\?$/.test(t) || /(인가요|할까요|있나요|맞나요|왜|어떻게)\b/.test(t)
    const isExplain =
      /(정의|공식|정리|핵심|즉|왜냐하면|때문에|예를 들면|개념|원리|중요)/.test(t) && !isQuestion
    if (isQuestion) return 'question' as const
    if (isExplain) return 'explain' as const
    return 'chitchat' as const
  }

  const teacherVsStudentEstimate = (s: string) => {
    const t = s.trim()
    if (!t) return 'unknown' as const
    if (/(해봅시다|정리합시다|볼게요|기억하세요|중요해요)/.test(t)) return 'teacher'
    if (/(저요|저는|모르겠어요|질문있어요|다시요)/.test(t)) return 'student'
    return 'teacher'
  }

  const timeline = useMemo(() => {
    const minutes = Math.max(10, Math.min(120, Math.round(classDurationMinutes)))
    const buckets = 9
    const bucketMinutes = minutes / buckets
    const text = transcriptText.trim()
    const parts = text
      ? text
          .split(/(?<=[.!?。…])\s+|\n+/)
          .map((x) => x.trim())
          .filter(Boolean)
      : []
    const rows = Array.from({ length: buckets }, () => ({
      explain: 0,
      question: 0,
      chitchat: 0,
      teacher: 0,
      student: 0,
      total: 0,
      minuteStart: 0,
      minuteEnd: 0,
    }))
    for (let i = 0; i < buckets; i++) {
      rows[i].minuteStart = Math.round(i * bucketMinutes)
      rows[i].minuteEnd = Math.round((i + 1) * bucketMinutes)
    }
    parts.forEach((p, idx) => {
      const b = Math.min(buckets - 1, Math.floor((idx / Math.max(parts.length, 1)) * buckets))
      const kind = classifySentence(p)
      const who = teacherVsStudentEstimate(p)
      rows[b].total += 1
      if (kind === 'explain') rows[b].explain += 1
      else if (kind === 'question') rows[b].question += 1
      else rows[b].chitchat += 1
      if (who === 'teacher') rows[b].teacher += 1
      if (who === 'student') rows[b].student += 1
    })

    const sum = rows.reduce(
      (acc, r) => {
        acc.explain += r.explain
        acc.question += r.question
        acc.chitchat += r.chitchat
        acc.teacher += r.teacher
        acc.student += r.student
        acc.total += r.total
        return acc
      },
      { explain: 0, question: 0, chitchat: 0, teacher: 0, student: 0, total: 0 },
    )

    const pct = (v: number) => (sum.total ? Math.round((v / sum.total) * 100) : 0)
    return {
      rows,
      summary: {
        explainPct: pct(sum.explain),
        questionPerMin: sum.total ? Math.round((sum.question / Math.max(minutes, 1)) * 10) / 10 : 0,
        chitchatPct: pct(sum.chitchat),
        teacherPct: sum.total ? Math.round((sum.teacher / sum.total) * 100) : 0,
        studentPct: sum.total ? Math.round((sum.student / sum.total) * 100) : 0,
      },
      minutes,
    }
  }, [classDurationMinutes, transcriptText])

  const subjectRisks = useMemo(() => {
    const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
    const base =
      (100 - riskInput.attendanceRate) * 0.28 +
      (100 - riskInput.classQualityScore) * 0.22 +
      (100 - riskInput.schoolEnvironmentScore) * 0.12

    const list = subjects.map((s) => {
      const scorePenalty = (100 - s.score) * 0.55
      const raw = base + scorePenalty
      const risk = clamp(Math.round(raw), 0, 100)
      const prob = clamp(Math.round(risk * 0.75), 0, 100)
      const priority = clamp01((risk / 100) * (s.importance ?? 1))
      return { ...s, risk, prob, priority }
    })
    const sorted = [...list].sort((a, b) => b.risk - a.risk)
    const top2 = sorted.slice(0, 2)
    const dropout = clamp(
      Math.round(
        (top2.reduce((a, s) => a + s.risk, 0) / Math.max(top2.length, 1)) * 0.78,
      ),
      0,
      100,
    )
    return { list: sorted, dropout }
  }, [subjects, riskInput.attendanceRate, riskInput.classQualityScore, riskInput.schoolEnvironmentScore, clamp])

  const handleAutoClassAnalysis = async () => {
    try {
      const data = await analyzeClassFromText(transcriptText)
      setClassInput(data.classInput)
      setAnalysisMeta(data.meta)
      setApiStatus((s) => ({ ...s, class_from_text: 'live' }))
      return
    } catch {
      const { input: autoInput, meta } = deriveClassInputFromTranscript(transcriptText)
      setClassInput(autoInput)
      setAnalysisMeta(meta)
      setApiStatus((s) => ({ ...s, class_from_text: 'local' }))
    }
  }

  const handleTranscribe = async () => {
    if (!audioFile || sttLoading) return
    setSttLoading(true)
    setSttError(null)
    try {
      const data = await transcribeAudio(audioFile, 'ko')
      if (data.transcript?.trim()) setTranscriptText(data.transcript.trim())
      setApiStatus((s) => ({ ...s, stt: 'live' }))
    } catch (e) {
      setSttError(`전사 실패: ${String(e)}`)
      setApiStatus((s) => ({ ...s, stt: 'error' }))
    } finally {
      setSttLoading(false)
    }
  }

  const handleRunFullPipeline = async () => {
    try {
      const data = await runFullPipeline({
        transcript: transcriptText,
        risk_input: riskInput,
        schedule_input: scheduleInput,
        twin_input: twinInput,
        causal_input: causalInput,
        xai_input: xaiInput,
      })
      setClassInput(data.classInput)
      setAnalysisMeta(data.analysisMeta)
      setRiskInput(data.riskInput)
      setScheduleInput(data.scheduleInput)
      setTwinInput(data.twinInput)
      setCausalInput(data.causalInput)
      setXaiInput(data.xaiInput)
      setTab('risk')
      setApiStatus((s) => ({ ...s, pipeline_run: 'live' }))
      return
    } catch {
      // 백엔드 비가용 시 로컬 계산으로 유지
      setApiStatus((s) => ({ ...s, pipeline_run: 'local' }))
    }

    const linkedRisk = {
      ...riskInput,
      classQualityScore: classResult.qualityScore,
    }
    const linkedRiskResult = predictRisk(linkedRisk)

    const linkedSchedule = {
      ...scheduleInput,
      koreanLevel: clamp(100 - linkedRiskResult.subjectRisk * 0.45, 35, 95),
      mathLevel: clamp(100 - linkedRiskResult.subjectRisk * 0.65, 30, 95),
      englishLevel: clamp(100 - linkedRiskResult.subjectRisk * 0.4, 35, 95),
      fatigue: clamp(
        Math.round((scheduleInput.fatigue * 0.7 + (100 - classResult.qualityScore) * 0.3) * 10) / 10,
        0,
        100,
      ),
    }
    const linkedScheduleResult = optimizeSchedule(linkedSchedule)

    const linkedTwin = {
      ...twinInput,
      planQuality: clamp(
        Math.round(classResult.qualityScore * 0.55 + (100 - linkedRiskResult.subjectRisk) * 0.45),
        35,
        95,
      ),
      consistency: clamp(Math.round(48 + linkedScheduleResult.effectiveHours * 8), 35, 95),
    }

    const linkedCausal = {
      attendanceImpact: clamp(Math.round(25 + (100 - linkedRisk.attendanceRate) * 0.8), 5, 60),
      classQualityImpact: clamp(Math.round((100 - classResult.qualityScore) * 0.7), 5, 60),
      selfStudyImpact: clamp(Math.round(18 + (100 - linkedTwin.consistency) * 0.4), 5, 60),
      environmentImpact: clamp(Math.round(100 - linkedRisk.schoolEnvironmentScore), 5, 40),
    }

    const linkedXai = {
      attendance: linkedRisk.attendanceRate,
      understanding: Math.round((linkedSchedule.mathLevel + linkedSchedule.koreanLevel) / 2),
      fatigue: linkedSchedule.fatigue,
      classQuality: classResult.qualityScore,
    }

    setRiskInput(linkedRisk)
    setScheduleInput(linkedSchedule)
    setTwinInput(linkedTwin)
    setCausalInput(linkedCausal)
    setXaiInput(linkedXai)
    setTab('risk')
  }

  const extractSchoolPrefix = (name: string, level: SchoolLevel) => {
    const s = name.trim()
    const removeSuffixes =
      level === 'elementary'
        ? [/초등학교$/g]
        : level === 'middle'
          ? [/중학교$/g]
          : level === 'high'
            ? [/고등학교$/g, /고교$/g]
            : [/초등학교$/g, /중학교$/g, /고등학교$/g, /고교$/g]

    let next = s
    for (const re of removeSuffixes) next = next.replace(re, '').trim()
    next = next.replace(/학교$/, '').trim()
    if (!next || next === s || next.length < 2) return null
    return next
  }

  const isSchoolLevelMatch = (name: string, level: SchoolLevel) => {
    if (level === 'all') return true
    if (level === 'elementary') return /초등학교/.test(name)
    if (level === 'middle') return /중학교/.test(name)
    return /고등학교|고교/.test(name)
  }

  const schoolLevelLabel = (level: SchoolLevel) => {
    if (level === 'elementary') return '초등'
    if (level === 'middle') return '중등'
    if (level === 'high') return '고등'
    return '전체'
  }

  const schoolLevelSuffix = (level: SchoolLevel) => {
    if (level === 'elementary') return '초등학교'
    if (level === 'middle') return '중학교'
    if (level === 'high') return '고등학교'
    return '학교'
  }

  const handleSearchSchools = async (overrideQuery?: string) => {
    const q = (overrideQuery ?? schoolQuery).trim()
    if (!q) return

    setSchoolSearchLoading(true)
    setSchoolSearchError(null)

    try {
      const data = await searchSchools(q)
      const all = Array.isArray(data.schools) ? data.schools : []
      const filtered = all.filter((s: { SCHUL_NM?: string }) => {
        if (typeof s.SCHUL_NM !== 'string') return false
        return isSchoolLevelMatch(s.SCHUL_NM, schoolLevel)
      })

      setSchoolResults(filtered)

      if (filtered.length === 0) {
        setSchoolSearchError(`${schoolLevelLabel(schoolLevel)} 학교 검색 결과가 없습니다.`)
        setRelatedChips([])
        return
      }

      const chips = Array.from(
        new Set(
          filtered
            .map((s: { SCHUL_NM?: string }) =>
              typeof s.SCHUL_NM === 'string' ? extractSchoolPrefix(s.SCHUL_NM, schoolLevel) : null,
            )
            .filter(Boolean),
        ),
      ).slice(0, 8) as string[]

      setRelatedChips(chips)
    } catch (e) {
      setSchoolSearchError(`학교 검색 실패: ${String(e)}`)
    } finally {
      setSchoolSearchLoading(false)
    }
  }

  useEffect(() => {
    if (tab !== 'stack') return
    const q = schoolQuery.trim()
    if (q.length < 2) {
      setSchoolResults([])
      setRelatedChips([])
      setSchoolSearchError(null)
      return
    }

    let active = true
    const id = window.setTimeout(() => {
      ;(async () => {
        try {
          await handleSearchSchools(q)
        } catch {
          // handleSearchSchools 내부에서 에러 처리
        }
        if (!active) return
      })()
    }, 250)

    return () => {
      active = false
      window.clearTimeout(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schoolQuery, tab, schoolLevel])

  const handleLoadPublicSummary = async () => {
    if (!selectedSchool) {
      setPublicSummary('먼저 학교를 선택하세요.')
      return
    }
    try {
      const data = await fetchPublicSummaryBySchool(
        selectedSchool.atptCode,
        selectedSchool.schoolCode,
      )
      setPublicSummary(JSON.stringify(data, null, 2))
      setNeisSummarySource(typeof (data as { source?: unknown }).source === 'string' ? (data as { source: string }).source : '—')
      setApiStatus((s) => ({ ...s, neis_summary: 'live' }))
    } catch (e) {
      setPublicSummary(`조회 실패: ${String(e)}`)
      setNeisSummarySource('')
      setApiStatus((s) => ({ ...s, neis_summary: 'error' }))
    }
  }

  const handleLoadTimetable = async () => {
    if (!selectedSchool) {
      setTimetableText('먼저 학교를 선택하세요.')
      return
    }
    try {
      const data = await fetchTimetable(selectedSchool.atptCode, selectedSchool.schoolCode)
      setTimetableText(JSON.stringify(data, null, 2))
      setTimetableSource(typeof (data as { source?: unknown }).source === 'string' ? (data as { source: string }).source : '—')
      setApiStatus((s) => ({ ...s, neis_timetable: 'live' }))

      // 데모: 시간표 구성으로 피로도/학습시간 기본값을 보정
      const rows = Array.isArray((data as any)?.rows) ? ((data as any).rows as any[]) : []
      const periods = rows
        .map((r) => Number(r?.PERIO))
        .filter((n) => Number.isFinite(n))
      const uniquePeriods = new Set(periods)
      const load = clamp(uniquePeriods.size * 10, 10, 70) // 1교시당 10 가중치
      setScheduleInput((p) => ({
        ...p,
        fatigue: clamp(Math.round((p.fatigue * 0.7 + load * 0.3) * 10) / 10, 0, 100),
        studyHours: clamp(
          Math.round((p.studyHours * 0.75 + (3.5 + uniquePeriods.size * 0.2) * 0.25) * 10) / 10,
          1,
          8,
        ),
      }))
    } catch (e) {
      setTimetableText(`시간표 조회 실패: ${String(e)}`)
      setTimetableSource('')
      setApiStatus((s) => ({ ...s, neis_timetable: 'error' }))
    }
  }

  const handleLoadKess = async () => {
    try {
      const data = await fetchKessStats({ region: '전국', year: new Date().getFullYear(), grade: 1 })
      setKessText(JSON.stringify(data, null, 2))
      setKessSource(typeof (data as { source?: unknown }).source === 'string' ? (data as { source: string }).source : '—')
      setApiStatus((s) => ({ ...s, kess: 'live' }))

      const avg = Number((data as any)?.metrics?.average_score)
      const gap = Number((data as any)?.metrics?.regional_gap)
      if (Number.isFinite(avg)) {
        setRiskInput((p) => ({
          ...p,
          averageScore: clamp(Math.round((p.averageScore * 0.7 + avg * 0.3) * 10) / 10, 0, 100),
        }))
      }
      if (Number.isFinite(gap)) {
        setRiskInput((p) => ({
          ...p,
          schoolEnvironmentScore: clamp(
            Math.round(p.schoolEnvironmentScore * 0.75 + (100 - gap * 2) * 0.25),
            0,
            100,
          ),
        }))
      }
    } catch (e) {
      setKessText(`KESS 조회 실패: ${String(e)}`)
      setKessSource('')
      setApiStatus((s) => ({ ...s, kess: 'error' }))
    }
  }

  const handleLoadAlimi = async () => {
    if (!selectedSchool) {
      setAlimiText('먼저 학교를 선택하세요.')
      return
    }
    try {
      const data = await fetchAlimiEnvironment({
        atpt_code: selectedSchool.atptCode,
        school_code: selectedSchool.schoolCode,
        school_name: selectedSchool.schoolName,
      })
      setAlimiText(JSON.stringify(data, null, 2))
      setAlimiSource(typeof (data as { source?: unknown }).source === 'string' ? (data as { source: string }).source : '—')
      setApiStatus((s) => ({ ...s, alimi: 'live' }))

      const env = Number((data as any)?.features?.environment_score)
      if (Number.isFinite(env)) {
        setRiskInput((p) => ({ ...p, schoolEnvironmentScore: clamp(Math.round(env), 0, 100) }))
      }
    } catch (e) {
      setAlimiText(`학교알리미(환경) 조회 실패: ${String(e)}`)
      setAlimiSource('')
      setApiStatus((s) => ({ ...s, alimi: 'error' }))
    }
  }

  const handleRunModelApis = async () => {
    try {
      const model = await predictRiskSklearn({
        averageScore: riskInput.averageScore,
        attendanceRate: riskInput.attendanceRate,
        classQualityScore: riskInput.classQualityScore,
        schoolEnvironmentScore: riskInput.schoolEnvironmentScore,
      })
      setModelText(JSON.stringify(model, null, 2))
      setApiStatus((s) => ({ ...s, sklearn: 'live' }))
    } catch (e) {
      setModelText(`Scikit-learn 예측 API 실패: ${String(e)}`)
      setApiStatus((s) => ({ ...s, sklearn: 'error' }))
    }

    try {
      const rl = await optimizeScheduleSb3({
        koreanLevel: scheduleInput.koreanLevel,
        mathLevel: scheduleInput.mathLevel,
        englishLevel: scheduleInput.englishLevel,
        fatigue: scheduleInput.fatigue,
        studyHours: scheduleInput.studyHours,
        objective: 'balanced',
      })
      setRlText(JSON.stringify(rl, null, 2))
      setApiStatus((s) => ({ ...s, sb3: 'live' }))
    } catch (e) {
      setRlText(`SB3 최적화 API 실패: ${String(e)}`)
      setApiStatus((s) => ({ ...s, sb3: 'error' }))
    }

    try {
      const shap = await explainShap({
        averageScore: riskInput.averageScore,
        attendanceRate: riskInput.attendanceRate,
        classQualityScore: riskInput.classQualityScore,
        schoolEnvironmentScore: riskInput.schoolEnvironmentScore,
      })
      setShapText(JSON.stringify(shap, null, 2))
      setApiStatus((s) => ({ ...s, shap: 'live' }))
    } catch (e) {
      setShapText(`SHAP 설명 API 실패: ${String(e)}`)
      setApiStatus((s) => ({ ...s, shap: 'error' }))
    }
  }

  const ApiBadge = ({ k }: { k: keyof typeof apiStatus }) => {
    const v = apiStatus[k]
    const label = v === 'live' ? 'LIVE' : v === 'local' ? 'LOCAL' : v === 'error' ? 'ERR' : '—'
    return <span className={`ai-badge ai-badge--${v}`}>{label}</span>
  }

  const stackStatusHint = (v: (typeof apiStatus)[keyof typeof apiStatus]) => {
    if (v === 'live') return '서버 응답 성공'
    if (v === 'local') return '로컬/폴백 처리'
    if (v === 'error') return '마지막 호출 실패'
    return '아직 호출 안 함'
  }

  const StackApiBadge = ({ k }: { k: keyof typeof apiStatus }) => {
    const v = apiStatus[k]
    const label = v === 'live' ? 'LIVE' : v === 'local' ? 'LOCAL' : v === 'error' ? 'ERR' : '미호출'
    return (
      <div className=ai-stack-api-status>
        <span className={`ai-badge ai-badge--${v}`}>{label}</span>
        <span className=ai-stack-api-status-hint>{stackStatusHint(v)}</span>
      </div>
    )
  }

  const exportScenario = () => {
    const payload = {
      version: 1 as const,
      exportedAt: new Date().toISOString(),
      tab,
      classInput,
      classDurationMinutes,
      riskInput,
      subjects,
      scheduleInput,
      twinInput,
      causalInput,
      xaiInput,
      transcriptText,
      analysisMeta,
      schoolQuery,
      schoolLevel,
      selectedSchool,
      messages,
      publicSummary,
      timetableText,
      kessText,
      alimiText,
      modelText,
      rlText,
      shapText,
      neisSummarySource,
      timetableSource,
      kessSource,
      alimiSource,
      stackDetailsOpen,
      apiStatus,
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `class-orbit-scenario-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const importScenarioFromFile = async (file: File) => {
    setScenarioImportError(null)
    const text = await file.text()
    const p = JSON.parse(text) as Record<string, unknown>
    if (p.version !== 1) throw new Error('지원하지 않는 시나리오 버전입니다.')

    if (typeof p.tab === 'string') setTab(p.tab as AiTab)
    if (p.classInput && typeof p.classInput === 'object') setClassInput(p.classInput as typeof classInput)
    if (typeof p.classDurationMinutes === 'number') setClassDurationMinutes(p.classDurationMinutes)
    if (p.riskInput && typeof p.riskInput === 'object') setRiskInput(p.riskInput as typeof riskInput)
    if (Array.isArray(p.subjects)) setSubjects(p.subjects as typeof subjects)
    if (p.scheduleInput && typeof p.scheduleInput === 'object') setScheduleInput(p.scheduleInput as typeof scheduleInput)
    if (p.twinInput && typeof p.twinInput === 'object') setTwinInput(p.twinInput as typeof twinInput)
    if (p.causalInput && typeof p.causalInput === 'object') setCausalInput(p.causalInput as typeof causalInput)
    if (p.xaiInput && typeof p.xaiInput === 'object') setXaiInput(p.xaiInput as typeof xaiInput)
    if (typeof p.transcriptText === 'string') setTranscriptText(p.transcriptText)
    if (p.analysisMeta && typeof p.analysisMeta === 'object') setAnalysisMeta(p.analysisMeta as typeof analysisMeta)
    if (typeof p.schoolQuery === 'string') setSchoolQuery(p.schoolQuery)
    if (typeof p.schoolLevel === 'string') setSchoolLevel(p.schoolLevel as SchoolLevel)
    if (p.selectedSchool === null) setSelectedSchool(null)
    else if (p.selectedSchool && typeof p.selectedSchool === 'object')
      setSelectedSchool(p.selectedSchool as NonNullable<typeof selectedSchool>)
    if (Array.isArray(p.messages)) setMessages(p.messages as ChatMessage[])
    if (typeof p.publicSummary === 'string') setPublicSummary(p.publicSummary)
    if (typeof p.timetableText === 'string') setTimetableText(p.timetableText)
    if (typeof p.kessText === 'string') setKessText(p.kessText)
    if (typeof p.alimiText === 'string') setAlimiText(p.alimiText)
    if (typeof p.modelText === 'string') setModelText(p.modelText)
    if (typeof p.rlText === 'string') setRlText(p.rlText)
    if (typeof p.shapText === 'string') setShapText(p.shapText)
    if (typeof p.neisSummarySource === 'string') setNeisSummarySource(p.neisSummarySource)
    if (typeof p.timetableSource === 'string') setTimetableSource(p.timetableSource)
    if (typeof p.kessSource === 'string') setKessSource(p.kessSource)
    if (typeof p.alimiSource === 'string') setAlimiSource(p.alimiSource)
    if (typeof p.stackDetailsOpen === 'boolean') setStackDetailsOpen(p.stackDetailsOpen)
    if (p.apiStatus && typeof p.apiStatus === 'object') {
      setApiStatus((prev) => ({ ...prev, ...(p.apiStatus as Partial<typeof prev>) }))
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const nextUser: ChatMessage = { role: 'user', content: text }
    const history = [...messages, nextUser]
    setMessages(history)
    setInput('')
    setLoading(true)

    const { answer, source } = await askAi(text, history)
    setMessages((prev) => [...prev, { role: 'assistant', content: answer }])
    setApiStatus((s) => ({ ...s, chat: source === 'live' ? 'live' : 'local' }))
    setLoading(false)
  }

  // ── 확장 탭 핸들러 ─────────────────────────────

  const handlePathwayRecommend = async () => {
    setPathwayLoading(true)
    setPathwayError(null)
    try {
      const res = await recommendPathway({
        grade: 2,
        subjects: pathwaySubjects,
        goal: pathwayGoal,
        studyHoursPerDay: pathwayHours,
      })
      setPathwayResult(res)
    } catch (e) {
      setPathwayError(e instanceof Error ? e.message : String(e))
    } finally {
      setPathwayLoading(false)
    }
  }

  const handleWarningCheck = async () => {
    setWarningLoading(true)
    setWarningError(null)
    try {
      const res = await checkWarning({
        recentScores: warningScores,
        attendanceRate: warningAttendance,
        submissionRate: warningSubmission,
        engagementScore: warningEngagement,
      })
      setWarningResult(res)
    } catch (e) {
      setWarningError(e instanceof Error ? e.message : String(e))
    } finally {
      setWarningLoading(false)
    }
  }

  const handleEquityFetch = async () => {
    setEquityLoading(true)
    setEquityError(null)
    try {
      const res = await fetchEquityIndex({
        region: equityRegion,
        schoolType: equitySchoolType,
        year: equityYear,
      })
      setEquityResult(res)
    } catch (e) {
      setEquityError(e instanceof Error ? e.message : String(e))
    } finally {
      setEquityLoading(false)
    }
  }

  const handleResourceMatch = async () => {
    setResourceLoading(true)
    setResourceError(null)
    try {
      const res = await matchResources({
        subject: resourceSubject,
        level: resourceLevel,
        grade: 2,
        formatPref: resourceFormat || undefined,
      })
      setResourceResult(res)
    } catch (e) {
      setResourceError(e instanceof Error ? e.message : String(e))
    } finally {
      setResourceLoading(false)
    }
  }

  const handleNlqSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const q = nlqInput.trim()
    if (!q || nlqLoading) return
    setNlqLoading(true)
    setNlqError(null)
    try {
      const res = await nlqQuery({ query: q, context: tab })
      setNlqResult(res)
      setNlqHistory((prev) => [{ query: q, result: res }, ...prev].slice(0, 10))
      setNlqInput('')
    } catch (e) {
      setNlqError(e instanceof Error ? e.message : String(e))
    } finally {
      setNlqLoading(false)
    }
  }

  return (
    <div className=ai-page ai2>
      <div className=ai-shell>
        <header className=ai-topbar>
          <div className=ai-topbar-left>
            <button
              type=button
              className=ai-topbar-iconbtn
              onClick={() => setNavOpen((v) => !v)}
              aria-label={navOpen ? '메뉴 닫기' : '메뉴 열기'}
              aria-expanded={navOpen}
            >
              ☰
            </button>
            <div className=ai-topbar-titlewrap>
              <p className=ai-topbar-kicker>AI Workspace</p>
              <h1 className=ai-topbar-title>Class Orbit</h1>
            </div>
          </div>
          <div className=ai-topbar-right>
            <span
              className=ai-topbar-apihint
              title=Vite 환경변수 VITE_API_BASE_URL (비어 있으면 현재 오리진으로 /api 호출)
            >
              {import.meta.env.VITE_API_BASE_URL?.trim()
                ? `API ${import.meta.env.VITE_API_BASE_URL.trim()}`
                : 'API same-origin'}
            </span>
            {tab === 'chat' ? (
              <>
                <ApiBadge k=chat />
                <span className=ai-topbar-meta>messages: {historyCount}</span>
              </>
            ) : null}
            <button type=button className=ai-topbar-btn onClick={onBack}>
              메인으로
            </button>
          </div>
        </header>

        <div className={`ai-layout${navOpen ? ' is-nav-open' : ''}`}>
          <aside className=ai-nav aria-label=AI 메뉴>
            <nav className=ai-nav-list aria-label=탭>
              {(Object.keys(TAB_LABELS) as AiTab[]).map((key) => (
                <button
                  key={key}
                  type=button
                  className={`ai-nav-item${tab === key ? ' is-active' : ''}`}
                  onClick={() => {
                    setTab(key)
                    setNavOpen(false)
                  }}
                >
                  {TAB_LABELS[key]}
                </button>
              ))}
            </nav>
          </aside>

          <main className=ai-content aria-label={`${TAB_LABELS[tab]} 화면`}>

          {tab === 'overview' ? (
            <section className=ai-board ai-board--overview>
              <article className=ai-card ai-card--hero>
                <p className=ai-card-kicker>Today</p>
                <h2>한 눈에 보는 요약</h2>
                <p>핵심 지표만 먼저 보고, 필요한 화면으로 이동하세요.</p>

                <div className=ai-overview-actions aria-label=빠른 이동>
                  {(
                    [
                      ['class-analysis', '수업 분석'],
                      ['risk', '격차 예측'],
                      ['schedule', '시간표'],
                      ['stack', '학교 데이터'],
                      ['chat', '대화'],
                    ] as const
                  ).map(([k, label]) => (
                    <button
                      key={k}
                      type=button
                      className=ai-overview-btn
                      onClick={() => setTab(k)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className=ai-scenario-row aria-label=시나리오 저장 및 불러오기>
                  <button type=button className=ai-overview-btn onClick={exportScenario}>
                    시나리오 저장 (JSON)
                  </button>
                  <button
                    type=button
                    className=ai-overview-btn
                    onClick={() => scenarioFileRef.current?.click()}
                  >
                    시나리오 불러오기
                  </button>
                  <input
                    ref={scenarioFileRef}
                    type=file
                    accept=application/json,.json
                    className=ai-file-input-hidden
                    aria-hidden
                    onChange={async (e) => {
                      const f = e.target.files?.[0]
                      e.target.value = ''
                      if (!f) return
                      try {
                        await importScenarioFromFile(f)
                      } catch (err) {
                        setScenarioImportError(
                          err instanceof Error ? err.message : `불러오기 실패: ${String(err)}`,
                        )
                      }
                    }}
                  />
                </div>
                {scenarioImportError ? (
                  <p className=ai-error-text role=alert>
                    {scenarioImportError}
                  </p>
                ) : null}

                <div className=ai-result ai-result--flat>
                  <div className=ai-metrics>
                    <div className=ai-metric>
                      <span className=ai-metric-kicker>Quality</span>
                      <span className=ai-metric-num>{classResult.qualityScore}</span>
                      <span className=ai-metric-unit>/100</span>
                    </div>
                    <div className=ai-metric>
                      <span className=ai-metric-kicker>Risk</span>
                      <span className=ai-metric-num>{riskResult.subjectRisk}%</span>
                      <span className=ai-metric-unit>overall</span>
                    </div>
                    <div className=ai-metric>
                      <span className=ai-metric-kicker>Study</span>
                      <span className=ai-metric-num>{scheduleResult.effectiveHours}</span>
                      <span className=ai-metric-unit>hrs/day</span>
                    </div>
                  </div>
                </div>
              </article>
            </section>
          ) : null}

          {tab === 'class-analysis' ? (
            <section className=ai-detail>
              <h2>1) 수업 분석 (Teacher Analytics)</h2>
              <div className=ai-split>
                <div className=ai-split-main>
                  <div className=ai-grid2>
                    <label className=ai-field>
                      수업 시간(분)
                      <span className=ai-field-help>45분, 50분 등 실제 수업 길이를 입력하세요.</span>
                      <input
                        type=number
                        value={classDurationMinutes}
                        onChange={(e) => setClassDurationMinutes(Number(e.target.value))}
                      />
                    </label>
                  </div>
                  <label className=ai-field>
                    수업 텍스트/전사본
                    <span className=ai-field-help>
                      텍스트만 넣어도 자동으로 문장/질문/반복을 추정해서 입력값을 채웁니다.
                    </span>
                    <div className=ai-stt-row aria-label=음성 전사>
                      <input
                        className=ai-file
                        type=file
                        accept=audio/*
                        onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                      />
                      <button
                        type=button
                        className=ai-send-btn ai-send-btn--ghost
                        onClick={handleTranscribe}
                        disabled={!audioFile || sttLoading}
                      >
                        {sttLoading ? '전사 중...' : '음성→텍스트'}
                      </button>
                      <ApiBadge k=stt />
                    </div>
                    {sttError ? <p className=ai-error-text>{sttError}</p> : null}
                    <textarea
                      className=ai-input ai-input--transcript
                      value={transcriptText}
                      onChange={(e) => setTranscriptText(e.target.value)}
                      rows={5}
                    />
                  </label>
                  <div className=ai-inline-actions>
                    <div className=ai-action-pair>
                      <button type=button className=ai-send-btn onClick={handleAutoClassAnalysis}>
                        자동 분석
                      </button>
                      <ApiBadge k=class_from_text />
                    </div>
                    <div className=ai-action-pair>
                      <button
                        type=button
                        className=ai-send-btn ai-send-btn--ghost
                        onClick={handleRunFullPipeline}
                      >
                        전체 파이프라인 실행
                      </button>
                      <ApiBadge k=pipeline_run />
                    </div>
                  </div>
                  <div className=ai-result>
                    <p className=ai-mini-kicker>시간대별 구조 (설명/질문/잡담)</p>
                    <div className=ai-timeline aria-label=시간대별 비율>
                      {timeline.rows.map((r) => {
                        const total = Math.max(r.total, 1)
                        const explainPct = Math.round((r.explain / total) * 100)
                        const questionPct = Math.round((r.question / total) * 100)
                        const chitchatPct = Math.max(0, 100 - explainPct - questionPct)
                        return (
                          <div key={`${r.minuteStart}-${r.minuteEnd}`} className=ai-tl-row>
                            <span className=ai-tl-label>
                              {r.minuteStart}–{r.minuteEnd}m
                            </span>
                            <div className=ai-tl-bar role=img aria-label=stacked bar>
                              <span className=ai-tl-seg ai-tl-seg--explain style={{ width: `${explainPct}%` }} />
                              <span className=ai-tl-seg ai-tl-seg--question style={{ width: `${questionPct}%` }} />
                              <span className=ai-tl-seg ai-tl-seg--chat style={{ width: `${chitchatPct}%` }} />
                            </div>
                            <span className=ai-tl-meta>
                              E {explainPct}%, Q {questionPct}%
                            </span>
                          </div>
                        )
                      })}
                    </div>
                    <CodeLines
                      title=teacher_analytics.summary
                      lines={[
                        {
                          key: 'duration_minutes',
                          value: timeline.minutes,
                          unit: 'min',
                          severity: 'info',
                        },
                        {
                          key: 'explanation_ratio',
                          value: `${timeline.summary.explainPct}%`,
                          note: '설명(개념/풀이) 비중',
                          severity: timeline.summary.explainPct >= 60 ? 'ok' : 'warn',
                        },
                        {
                          key: 'question_index',
                          value: timeline.summary.questionPerMin,
                          unit: '/min',
                          note: '질문 유도 빈도(시간 보정)',
                          severity: timeline.summary.questionPerMin >= 0.25 ? 'ok' : 'warn',
                        },
                        {
                          key: 'speaker_mix',
                          value: `${timeline.summary.teacherPct}/${timeline.summary.studentPct}`,
                          unit: '%',
                          note: '교사/학생 발화 추정',
                          severity: 'info',
                        },
                      ]}
                    />
                  </div>
                  <div className=ai-grid2>
                    <label className=ai-field>
                      transcript length
                      <span className=ai-field-help>
                        전사 텍스트 길이(대략적). 길수록 안정적인 추정이 됩니다.
                      </span>
                      <input
                        type=number
                        value={classInput.transcriptLength}
                        onChange={(e) =>
                          setClassInput((p) => ({ ...p, transcriptLength: Number(e.target.value) }))
                        }
                      />
                    </label>
                    <label className=ai-field>
                      explanation focus %
                      <span className=ai-field-help>
                        설명(개념/풀이) 중심 비율. 높을수록 “잡담 대비 설명”이 많습니다.
                      </span>
                      <input
                        type=number
                        value={classInput.explanationFocus}
                        onChange={(e) =>
                          setClassInput((p) => ({ ...p, explanationFocus: Number(e.target.value) }))
                        }
                      />
                    </label>
                    <label className=ai-field>
                      repetition count
                      <span className=ai-field-help>
                        반복 문장/패턴 수. 너무 높으면 비효율, 너무 낮으면 강조 부족일 수 있습니다.
                      </span>
                      <input
                        type=number
                        value={classInput.repetitionCount}
                        onChange={(e) =>
                          setClassInput((p) => ({ ...p, repetitionCount: Number(e.target.value) }))
                        }
                      />
                    </label>
                    <label className=ai-field>
                      question prompt %
                      <span className=ai-field-help>
                        질문 유도/확인 질문 비율. 상호작용이 높을수록 이해 확인에 유리합니다.
                      </span>
                      <input
                        type=number
                        value={classInput.questionPromptRate}
                        onChange={(e) =>
                          setClassInput((p) => ({ ...p, questionPromptRate: Number(e.target.value) }))
                        }
                      />
                    </label>
                    <label className=ai-field>
                      keyword density %
                      <span className=ai-field-help>
                        핵심 키워드 등장 밀도. 너무 높으면 과밀, 너무 낮으면 핵심이 흐려질 수 있습니다.
                      </span>
                      <input
                        type=number
                        value={classInput.keywordDensity}
                        onChange={(e) =>
                          setClassInput((p) => ({ ...p, keywordDensity: Number(e.target.value) }))
                        }
                      />
                    </label>
                  </div>
                  <div className=ai-result>
                    <CodeLines
                      title=teacher_analytics.metrics
                      lines={[
                        {
                          key: 'quality_score',
                          value: classResult.qualityScore,
                          unit: '/100',
                          note: '수업 구조 종합 점수',
                          severity:
                            classResult.qualityScore >= 80
                              ? 'ok'
                              : classResult.qualityScore >= 60
                                ? 'info'
                                : 'warn',
                        },
                        {
                          key: 'explanation_ratio',
                          value: `${classResult.explanationRatio}%`,
                          note: '설명 중심 비율',
                          severity: classResult.explanationRatio >= 60 ? 'ok' : 'warn',
                        },
                        {
                          key: 'sentences',
                          value: analysisMeta.sentenceCount,
                          note: '문장 수(추정)',
                          severity: 'info',
                        },
                        {
                          key: 'questions',
                          value: analysisMeta.questionCount,
                          note: '질문 문장 수(추정)',
                          severity: analysisMeta.questionCount >= 4 ? 'ok' : 'warn',
                        },
                        {
                          key: 'repetition',
                          value: analysisMeta.repeatedSentenceCount,
                          note: '반복 문장 수(추정)',
                          severity: analysisMeta.repeatedSentenceCount >= 8 ? 'warn' : 'info',
                        },
                      ]}
                    />

                    <div className=ai-chart-bars aria-label=Class charts>
                      <div className=ai-bar-row>
                        <span className=ai-bar-label>Quality</span>
                        <div className=ai-bar-track>
                          <div className=ai-bar-fill style={{ width: `${classResult.qualityScore}%` }} />
                        </div>
                        <span className=ai-bar-value>{classResult.qualityScore}/100</span>
                      </div>

                      <div className=ai-bar-row>
                        <span className=ai-bar-label>Explanation</span>
                        <div className=ai-bar-track>
                          <div className=ai-bar-fill style={{ width: `${classResult.explanationRatio}%` }} />
                        </div>
                        <span className=ai-bar-value>{classResult.explanationRatio}%</span>
                      </div>
                    </div>

                    <div className=ai-metric-feedback>
                      <span className=ai-metric-kicker>Feedback</span>
                      <p className=ai-metric-text>{classResult.feedback}</p>
                    </div>
                  </div>
                </div>

                <HelpPanel
                  title=수업 분석 지표 해석
                  items={[
                    {
                      term: 'Quality (/100)',
                      meaning:
                        '설명 중심/질문 유도/키워드 밀도/반복 패턴을 종합해 “수업 품질”로 환산한 점수입니다.',
                      tip: '70↑ 안정적, 50↓는 구조(설명 흐름/확인 질문)를 손보는 게 효과적입니다.',
                    },
                    {
                      term: 'Explanation (%)',
                      meaning:
                        '수업 텍스트에서 “설명/개념 전달”에 해당하는 비율로, 잡담 대비 설명 집중도를 의미합니다.',
                    },
                    {
                      term: 'Questions / Repetition',
                      meaning:
                        '상호작용(질문)과 강조(반복) 정도를 나타냅니다. 둘 다 “너무 높거나 낮으면” 수업 리듬이 깨질 수 있습니다.',
                    },
                    {
                      term: 'Keyword density (%)',
                      meaning:
                        '핵심 용어가 어느 정도 반복 등장하는지의 밀도입니다(핵심이 드러나는지 vs 과밀인지).',
                    },
                  ]}
                />
              </div>
            </section>
          ) : null}

          {tab === 'risk' ? (
            <section className=ai-detail>
              <h2>2) 학습 격차 예측 모델</h2>
              <div className=ai-split>
                <div className=ai-split-main>
                  <div className=ai-result>
                    <p className=ai-mini-kicker>과목 구성</p>
                    <div className=ai-subject-toolbar>
                      <input
                        className=ai-inline-input
                        placeholder=과목 추가 (예: 물리, 화학, 일본어...)
                        value={newSubjectName}
                        onChange={(e) => setNewSubjectName(e.target.value)}
                      />
                      <button
                        type=button
                        className=ai-send-btn ai-send-btn--ghost
                        onClick={() => {
                          const name = newSubjectName.trim()
                          if (!name) return
                          const id = `${name}-${Math.random().toString(16).slice(2, 7)}`
                          setSubjects((prev) => [
                            ...prev,
                            { id, name, score: 70, importance: 1.0 },
                          ])
                          setNewSubjectName('')
                        }}
                      >
                        추가
                      </button>
                    </div>
                    <div className=ai-subject-grid>
                      {subjects.map((s) => (
                        <div key={s.id} className=ai-subject-card>
                          <div className=ai-subject-head>
                            <span className=ai-subject-name>{s.name}</span>
                            <button
                              type=button
                              className=ai-xbtn
                              onClick={() => setSubjects((p) => p.filter((x) => x.id !== s.id))}
                              aria-label=과목 삭제
                              title=삭제
                            >
                              ×
                            </button>
                          </div>
                          <label className=ai-field>
                            성적(0~100)
                            <input
                              type=number
                              value={s.score}
                              onChange={(e) => {
                                const v = Number(e.target.value)
                                setSubjects((p) => p.map((x) => (x.id === s.id ? { ...x, score: v } : x)))
                              }}
                            />
                          </label>
                          <label className=ai-field>
                            중요도(0.5~1.5)
                            <input
                              type=number
                              step=0.05
                              value={s.importance}
                              onChange={(e) => {
                                const v = Number(e.target.value)
                                setSubjects((p) => p.map((x) => (x.id === s.id ? { ...x, importance: v } : x)))
                              }}
                            />
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className=ai-grid2>
                    <label className=ai-field>
                      평균 성적
                      <span className=ai-field-help>최근 성적의 평균(0~100). 낮을수록 위험도가 올라갑니다.</span>
                      <input
                        type=number
                        value={riskInput.averageScore}
                        onChange={(e) => setRiskInput((p) => ({ ...p, averageScore: Number(e.target.value) }))}
                      />
                    </label>
                    <label className=ai-field>
                      출결률
                      <span className=ai-field-help>출석률(0~100). 낮을수록 학습 리스크가 증가합니다.</span>
                      <input
                        type=number
                        value={riskInput.attendanceRate}
                        onChange={(e) => setRiskInput((p) => ({ ...p, attendanceRate: Number(e.target.value) }))}
                      />
                    </label>
                    <label className=ai-field>
                      수업 품질 점수
                      <span className=ai-field-help>수업 분석에서 나온 품질 점수(0~100). 낮을수록 위험도가 올라갑니다.</span>
                      <input
                        type=number
                        value={riskInput.classQualityScore}
                        onChange={(e) => setRiskInput((p) => ({ ...p, classQualityScore: Number(e.target.value) }))}
                      />
                    </label>
                    <label className=ai-field>
                      학교 환경 점수
                      <span className=ai-field-help>학습 환경/지원 정도(0~100). 낮을수록 위험도가 올라갑니다.</span>
                      <input
                        type=number
                        value={riskInput.schoolEnvironmentScore}
                        onChange={(e) =>
                          setRiskInput((p) => ({ ...p, schoolEnvironmentScore: Number(e.target.value) }))
                        }
                      />
                    </label>
                  </div>

                  <div className=ai-result>
                    <CodeLines
                      title=risk_prediction.summary
                      lines={[
                        {
                          key: 'overall_risk',
                          value: `${riskResult.subjectRisk}%`,
                          note: '환경, 출결, 수업 품질 기반',
                          severity:
                            riskResult.level === 'high'
                              ? 'error'
                              : riskResult.level === 'medium'
                                ? 'warn'
                                : 'ok',
                        },
                        {
                          key: 'dropout_by_subjects',
                          value: `${subjectRisks.dropout}%`,
                          note: '상위 위험 과목 기반 추정',
                          severity: subjectRisks.dropout >= 60 ? 'warn' : 'info',
                        },
                        {
                          key: 'dropout_overall',
                          value: `${riskResult.dropoutProbability}%`,
                          note: '전체 입력 기반 추정',
                          severity: riskResult.dropoutProbability >= 60 ? 'warn' : 'info',
                        },
                        {
                          key: 'tier',
                          value: riskResult.level.toUpperCase(),
                          note: 'LOW / MID / HIGH',
                          severity: 'info',
                        },
                      ]}
                    />

                    <div className=ai-chart-bars aria-label=Risk charts>
                      <p className=ai-mini-kicker>과목별 위험도</p>
                      <div className=ai-risk-list role=list>
                        {subjectRisks.list.map((s) => (
                          <div key={s.id} className=ai-risk-row role=listitem>
                            <span className=ai-risk-name>{s.name}</span>
                            <div className=ai-bar-track>
                              <div className=ai-bar-fill style={{ width: `${s.risk}%` }} />
                            </div>
                            <span className=ai-risk-val>{s.risk}%</span>
                          </div>
                        ))}
                      </div>
                      <div className=ai-bar-row>
                        <span className=ai-bar-label>Risk</span>
                        <div className=ai-bar-track>
                          <div className=ai-bar-fill style={{ width: `${riskResult.subjectRisk}%` }} />
                        </div>
                        <span className=ai-bar-value>{riskResult.subjectRisk}%</span>
                      </div>

                      <div className=ai-bar-row>
                        <span className=ai-bar-label>Dropout</span>
                        <div className=ai-bar-track>
                          <div className=ai-bar-fill style={{ width: `${riskResult.dropoutProbability}%` }} />
                        </div>
                        <span className=ai-bar-value>{riskResult.dropoutProbability}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                <HelpPanel
                  title=격차/탈락 리스크 해석
                  items={[
                    {
                      term: 'Risk (%)',
                      meaning:
                        '현재 입력(성적/출결/수업품질/환경)을 종합한 “학습 격차 확대 위험도”입니다.',
                      tip: '리스크가 높으면 “출결 개선”과 “기초 이해도 회복(시간표 재배치)”이 우선입니다.',
                    },
                    {
                      term: 'Dropout (%)',
                      meaning: '학습 이탈(지속 학습 실패) 확률을 가정한 지표입니다.',
                    },
                    {
                      term: 'Level',
                      meaning: 'LOW/MID/HIGH로 위험 티어를 요약합니다.',
                    },
                  ]}
                />
              </div>
            </section>
          ) : null}

          {tab === 'schedule' ? (
            <section className=ai-detail>
              <h2>3) 시간표 최적화 AI (강화학습 구조)</h2>
              <div className=ai-grid2>
                {(
                  [
                    ['koreanLevel', '국어 이해도'],
                    ['mathLevel', '수학 이해도'],
                    ['englishLevel', '영어 이해도'],
                    ['fatigue', '피로도'],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className=ai-field>
                    {label}
                    <input
                      type=number
                      value={scheduleInput[key]}
                      onChange={(e) =>
                        setScheduleInput((p) => ({ ...p, [key]: Number(e.target.value) }))
                      }
                    />
                  </label>
                ))}
                <label className=ai-field>
                  주간 학습 가능 시간
                  <input
                    type=number
                    step=0.5
                    value={scheduleInput.studyHours}
                    onChange={(e) =>
                      setScheduleInput((p) => ({ ...p, studyHours: Number(e.target.value) }))
                    }
                  />
                </label>
              </div>
              <div className=ai-result>
                <div className=ai-metrics>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Effective hours</span>
                    <span className=ai-metric-num>{scheduleResult.effectiveHours}h</span>
                    <span className=ai-metric-unit>this week</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Fatigue</span>
                    <span className=ai-metric-num>{scheduleInput.fatigue}</span>
                    <span className=ai-metric-unit>level</span>
                  </div>
                </div>

                <div className=ai-metric-feedback>
                  <span className=ai-metric-kicker>Routine</span>
                  {scheduleResult.routine.map((line) => (
                    <p key={line} className=ai-metric-text>
                      - {line}
                    </p>
                  ))}
                </div>
              </div>
            </section>
          ) : null}

          {tab === 'twin' ? (
            <section className=ai-detail>
              <h2>4) 학습 디지털 트윈</h2>
              <div className=ai-grid2>
                {(
                  [
                    ['currentAverage', '현재 평균'],
                    ['planQuality', '시간표 품질'],
                    ['consistency', '지속 학습'],
                    ['weeks', '시뮬레이션 주차'],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className=ai-field>
                    {label}
                    <input
                      type=number
                      value={twinInput[key]}
                      onChange={(e) =>
                        setTwinInput((p) => ({ ...p, [key]: Number(e.target.value) }))
                      }
                    />
                  </label>
                ))}
              </div>
              <div className=ai-result>
                <div className=ai-metrics>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Predicted</span>
                    <span className=ai-metric-num>{twinResult.predictedAverage}</span>
                    <span className=ai-metric-unit>avg</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Delta</span>
                    <span className=ai-metric-num>
                      {twinResult.delta > 0 ? `+${twinResult.delta}` : twinResult.delta}
                    </span>
                    <span className=ai-metric-unit>change</span>
                  </div>
                </div>

                <div className=ai-metric-feedback>
                  <span className=ai-metric-kicker>Twin</span>
                  <p className=ai-metric-text>{twinResult.comment}</p>
                </div>
              </div>
            </section>
          ) : null}

          {tab === 'causal' ? (
            <section className=ai-detail>
              <h2>5) 인과 분석 모델 (Causal AI)</h2>
              <div className=ai-grid2>
                {(
                  [
                    ['attendanceImpact', '출결 영향도'],
                    ['classQualityImpact', '수업 품질 영향도'],
                    ['selfStudyImpact', '자기주도 영향도'],
                    ['environmentImpact', '환경 영향도'],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className=ai-field>
                    {label}
                    <input
                      type=number
                      value={causalInput[key]}
                      onChange={(e) =>
                        setCausalInput((p) => ({ ...p, [key]: Number(e.target.value) }))
                      }
                    />
                  </label>
                ))}
              </div>
              <div className=ai-result>
                <div className=ai-metrics>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Top driver</span>
                    <span className=ai-metric-num>{causalResult.topDriver}</span>
                    <span className=ai-metric-unit>factor</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Weight</span>
                    <span className=ai-metric-num>{causalResult.topWeight}%</span>
                    <span className=ai-metric-unit>relative</span>
                  </div>
                </div>

                <div className=ai-metric-feedback>
                  <span className=ai-metric-kicker>Summary</span>
                  <p className=ai-metric-text>{causalResult.summary}</p>
                </div>
              </div>
            </section>
          ) : null}

          {tab === 'xai' ? (
            <section className=ai-detail>
              <h2>6) 설명 가능한 AI (Explainable AI)</h2>
              <div className=ai-grid2>
                {(
                  [
                    ['attendance', '출결'],
                    ['understanding', '이해도'],
                    ['fatigue', '피로도'],
                    ['classQuality', '수업 품질'],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className=ai-field>
                    {label}
                    <input
                      type=number
                      value={xaiInput[key]}
                      onChange={(e) =>
                        setXaiInput((p) => ({ ...p, [key]: Number(e.target.value) }))
                      }
                    />
                  </label>
                ))}
              </div>
              <div className=ai-result>
                <div className=ai-metrics>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Attendance</span>
                    <span className=ai-metric-num>{xaiResult.attendance}%</span>
                    <span className=ai-metric-unit>impact</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Understanding</span>
                    <span className=ai-metric-num>{xaiResult.understanding}%</span>
                    <span className=ai-metric-unit>impact</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Fatigue</span>
                    <span className=ai-metric-num>{xaiResult.fatigue}%</span>
                    <span className=ai-metric-unit>impact</span>
                  </div>
                  <div className=ai-metric>
                    <span className=ai-metric-kicker>Class quality</span>
                    <span className=ai-metric-num>{xaiResult.classQuality}%</span>
                    <span className=ai-metric-unit>impact</span>
                  </div>
                </div>
              </div>
            </section>
          ) : null}

          {tab === 'stack' ? (
            <section className=ai-detail ai-stack-page>
              <header className=ai-stack-header>
                <p className=ai-stack-eyebrow>학교 데이터</p>
                <h2>공공 API / 모델 연동</h2>
                <p className=ai-stack-intro>
                  <strong className=ai-stack-intro-strong>NEIS</strong>는 키와 학교 코드가 있으면 실데이터를
                  불러옵니다. <strong className=ai-stack-intro-strong>KESS, 알리미, 모델</strong>은 데모용
                  샘플 또는 시뮬레이션입니다. 전체 상태는{' '}
                  <code className=ai-inline-code>GET /api/health</code> 로 확인할 수 있습니다.
                </p>
              </header>

              <div className=ai-stack-card>
                <div className=ai-stack-card-head>
                  <span className=ai-stack-step>1</span>
                  <div>
                    <h3 className=ai-stack-card-title>학교 찾기</h3>
                    <p className=ai-stack-card-desc>급별로 검색한 뒤 목록에서 학교를 고릅니다.</p>
                  </div>
                </div>
                <div className=ai-level-row aria-label=학교급 선택>
                  {(
                    [
                      ['high', '고등'],
                      ['middle', '중등'],
                      ['elementary', '초등'],
                      ['all', '전체'],
                    ] as const
                  ).map(([lvl, label]) => (
                    <button
                      key={lvl}
                      type=button
                      className={`ai-level-btn${schoolLevel === lvl ? ' is-active' : ''}`}
                      onClick={() => {
                        setSchoolLevel(lvl)
                        setSchoolSuggestOpen(true)
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className=ai-stack-search-row>
                  <div className=ai-autocomplete-wrap ai-stack-search-input>
                    <input
                      className=ai-inline-input
                      placeholder={`학교명 (${schoolLevelLabel(schoolLevel)}, 예: 서울${schoolLevelSuffix(schoolLevel)})`}
                      value={schoolQuery}
                      onChange={(e) => setSchoolQuery(e.target.value)}
                      onFocus={() => setSchoolSuggestOpen(true)}
                      onBlur={() => window.setTimeout(() => setSchoolSuggestOpen(false), 140)}
                    />
                    {schoolSuggestOpen ? (
                      schoolSearchLoading ? (
                        <div className=ai-suggest-box>
                          <button type=button className=ai-suggest-item disabled>
                            검색 중...
                          </button>
                        </div>
                      ) : schoolResults.length > 0 ? (
                        <div className=ai-suggest-box>
                          {schoolResults.slice(0, 8).map((s) => (
                            <button
                              key={`${s.ATPT_OFCDC_SC_CODE}-${s.SD_SCHUL_CODE}`}
                              type=button
                              className=ai-suggest-item
                              onMouseDown={(e) => e.preventDefault()}
                              onClick={() => {
                                setSelectedSchool({
                                  atptCode: s.ATPT_OFCDC_SC_CODE,
                                  schoolCode: s.SD_SCHUL_CODE,
                                  schoolName: s.SCHUL_NM,
                                })
                                setSchoolQuery(s.SCHUL_NM)
                                setSchoolSuggestOpen(false)
                              }}
                            >
                              {s.SCHUL_NM}
                              <span className=ai-suggest-sub>{s.ATPT_OFCDC_SC_NM}</span>
                            </button>
                          ))}
                        </div>
                      ) : null
                    ) : null}
                  </div>
                  <button
                    type=button
                    className=ai-send-btn ai-send-btn--ghost ai-stack-search-btn
                    onClick={() => handleSearchSchools()}
                  >
                    검색 실행
                  </button>
                </div>
                {relatedChips.length > 0 && schoolQuery.trim().length >= 1 ? (
                  <div className=ai-chip-row aria-label=연관검색어>
                    {relatedChips.map((c) => (
                      <button
                        key={c}
                        type=button
                        className=ai-chip-btn
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => {
                          setSchoolQuery(c)
                          setSchoolSuggestOpen(true)
                        }}
                      >
                        {c}
                        {schoolLevelSuffix(schoolLevel)}
                      </button>
                    ))}
                  </div>
                ) : null}
                {schoolSearchError ? <p className=ai-error-text>{schoolSearchError}</p> : null}
                {schoolResults.length > 0 ? (
                  <div className=ai-stack-school-block>
                    <p className=ai-stack-sublabel>검색 결과에서 선택</p>
                    <div className=ai-school-list>
                      {schoolResults.map((s) => (
                        <button
                          key={`${s.ATPT_OFCDC_SC_CODE}-${s.SD_SCHUL_CODE}`}
                          type=button
                          className={`ai-school-btn${
                            selectedSchool?.atptCode === s.ATPT_OFCDC_SC_CODE &&
                            selectedSchool?.schoolCode === s.SD_SCHUL_CODE
                              ? ' is-active'
                              : ''
                          }`}
                          onClick={() =>
                            setSelectedSchool({
                              atptCode: s.ATPT_OFCDC_SC_CODE,
                              schoolCode: s.SD_SCHUL_CODE,
                              schoolName: s.SCHUL_NM,
                            })
                          }
                        >
                          {s.SCHUL_NM} ({s.ATPT_OFCDC_SC_NM}) [{s.ATPT_OFCDC_SC_CODE} / {s.SD_SCHUL_CODE}]
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className=ai-stack-card>
                <div className=ai-stack-card-head>
                  <span className=ai-stack-step>2</span>
                  <div>
                    <h3 className=ai-stack-card-title>NEIS, 학교 정보</h3>
                    <p className=ai-stack-card-desc>선택한 학교 기준으로 요약과 시간표를 가져옵니다.</p>
                  </div>
                </div>
                <p className=ai-stack-legend role=note>
                  초록 <strong>LIVE</strong>는 &quot;그 API를 눌렀을 때 서버가 정상 응답&quot;이지, 버튼이
                  선택된 상태가 아닙니다. <strong>미호출</strong>이면 아직 그 줄을 실행하지 않은 것입니다.
                </p>
                <div className=ai-stack-actions>
                  <div className=ai-stack-action>
                    <button type=button className=ai-send-btn onClick={handleLoadPublicSummary}>
                      학교 요약
                    </button>
                    <StackApiBadge k=neis_summary />
                  </div>
                  <div className=ai-stack-action>
                    <button type=button className=ai-send-btn ai-send-btn--ghost onClick={handleLoadTimetable}>
                      오늘 시간표
                    </button>
                    <StackApiBadge k=neis_timetable />
                  </div>
                </div>
              </div>

              <div className=ai-stack-card>
                <div className=ai-stack-card-head>
                  <span className=ai-stack-step>3</span>
                  <div>
                    <h3 className=ai-stack-card-title>통계, 환경 (샘플)</h3>
                    <p className=ai-stack-card-desc>실연동 전 데모 응답입니다.</p>
                  </div>
                </div>
                <div className=ai-stack-actions>
                  <div className=ai-stack-action>
                    <button type=button className=ai-send-btn ai-send-btn--ghost onClick={handleLoadKess}>
                      KESS 통계
                    </button>
                    <StackApiBadge k=kess />
                  </div>
                  <div className=ai-stack-action>
                    <button type=button className=ai-send-btn ai-send-btn--ghost onClick={handleLoadAlimi}>
                      학교알리미 환경
                    </button>
                    <StackApiBadge k=alimi />
                  </div>
                </div>
              </div>

              <div className=ai-stack-card ai-stack-card--accent>
                <div className=ai-stack-card-head>
                  <span className=ai-stack-step>4</span>
                  <div>
                    <h3 className=ai-stack-card-title>모델 파이프라인 (시뮬)</h3>
                    <p className=ai-stack-card-desc>리스크, 시간표, 설명 API를 한 번에 호출합니다.</p>
                  </div>
                </div>
                <div className=ai-stack-model-run>
                  <button type=button className=ai-send-btn ai-stack-model-btn onClick={handleRunModelApis}>
                    sklearn / SB3 / SHAP 실행
                  </button>
                  <div className=ai-stack-model-statuses aria-label=모델별 마지막 호출 상태>
                    <div className=ai-stack-model-line>
                      <span className=ai-stack-model-name>리스크 예측</span>
                      <StackApiBadge k=sklearn />
                    </div>
                    <div className=ai-stack-model-line>
                      <span className=ai-stack-model-name>시간표 최적</span>
                      <StackApiBadge k=sb3 />
                    </div>
                    <div className=ai-stack-model-line>
                      <span className=ai-stack-model-name>설명(SHAP)</span>
                      <StackApiBadge k=shap />
                    </div>
                  </div>
                </div>
              </div>

              <div className=ai-stack-card ai-stack-card--footer>
                <div className=ai-stack-selected>
                  <span className=ai-stack-sublabel>선택된 학교</span>
                  <p className=ai-stack-selected-value>
                    {selectedSchool
                      ? `${selectedSchool.schoolName}, ${selectedSchool.atptCode} / ${selectedSchool.schoolCode}`
                      : '학교를 먼저 선택하세요'}
                  </p>
                </div>
                <button
                  type=button
                  className={`ai-overview-btn ai-stack-toggle${stackDetailsOpen ? ' is-open' : ''}`}
                  onClick={() => setStackDetailsOpen((v) => !v)}
                  aria-expanded={stackDetailsOpen}
                >
                  {stackDetailsOpen ? 'JSON 응답 접기' : 'JSON 응답 보기'}
                </button>
                {stackDetailsOpen ? (
                  <div className=ai-stack-json>
                    <p>공공데이터 조회 결과:</p>
                    <p className=ai-source-line>
                      응답 출처: <strong>{neisSummarySource || '—'}</strong>
                    </p>
                    <pre className=ai-pre>{publicSummary}</pre>
                    <p>시간표 조회 결과:</p>
                    <p className=ai-source-line>
                      응답 출처: <strong>{timetableSource || '—'}</strong>
                    </p>
                    <pre className=ai-pre>{timetableText}</pre>
                    <p>KESS(교육통계) 조회 결과:</p>
                    <p className=ai-source-line>
                      응답 출처: <strong>{kessSource || '—'}</strong>
                    </p>
                    <pre className=ai-pre>{kessText}</pre>
                    <p>학교알리미(환경) 조회 결과:</p>
                    <p className=ai-source-line>
                      응답 출처: <strong>{alimiSource || '—'}</strong>
                    </p>
                    <pre className=ai-pre>{alimiText}</pre>
                    <p>Scikit-learn 예측 (시뮬레이션, 학습 모델 전까지 휴리스틱):</p>
                    <pre className=ai-pre>{modelText}</pre>
                    <p>SB3 강화학습 최적화 (시뮬레이션, RL 정책 전까지 휴리스틱):</p>
                    <pre className=ai-pre>{rlText}</pre>
                    <p>SHAP 설명 (시뮬레이션, shap 연동 전까지 근사치):</p>
                    <pre className=ai-pre>{shapText}</pre>
                  </div>
                ) : null}
              </div>
            </section>
          ) : null}

          {tab === 'chat' ? (
            <>
              <section className=ai-chat-log aria-live=polite>
                {messages.map((m, i) => (
                  <article key={`${m.role}-${i}`} className={`ai-msg ai-msg--${m.role}`}>
                    <p className=ai-msg-role>{m.role === 'user' ? 'You' : 'AI'}</p>
                    <p className=ai-msg-body>{m.content}</p>
                  </article>
                ))}
                {loading ? (
                  <article className=ai-msg ai-msg--assistant>
                    <p className=ai-msg-role>AI</p>
                    <p className=ai-msg-body>응답 생성 중...</p>
                  </article>
                ) : null}
              </section>

              <form className=ai-chat-form onSubmit={handleSubmit}>
                <textarea
                  className=ai-input
                  placeholder=질문을 입력하세요. 예) 학생별 취약 과목 예측 로직 설명해줘
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  rows={3}
                />
                <button type=submit className=ai-send-btn disabled={!canSend}>
                  Send
                </button>
              </form>
            </>
          ) : null}

          {/* ── 학습 경로 탭 ─────────────────────────── */}
          {tab === 'pathway' ? (
            <div className=ai-panel-grid>
              <section className=ai-panel>
                <header className=ai-panel-head><span className=ai-panel-kicker>Learning Pathway</span><h2 className=ai-panel-title>학습 경로 엔진</h2></header>
                <div className=ai-panel-body>
                  <label className=ai-label>목표
                    <select className=ai-select value={pathwayGoal} onChange={(e) => setPathwayGoal(e.target.value)}>
                      {['내신', '수능', '기초', '심화'].map((g) => <option key={g}>{g}</option>)}
                    </select>
                  </label>
                  <label className=ai-label>일일 학습 시간 (h)
                    <input className=ai-number type=number min={0.5} max={12} step={0.5} value={pathwayHours}
                      onChange={(e) => setPathwayHours(Number(e.target.value))} />
                  </label>
                  <p className=ai-sublabel>과목별 현재 성취도</p>
                  {pathwaySubjects.map((s, i) => (
                    <div key={s.subject} className=ai-row-inline>
                      <span className=ai-row-label>{s.subject}</span>
                      <input className=ai-range type=range min={0} max={100}
                        value={s.score}
                        onChange={(e) => setPathwaySubjects((prev) => prev.map((x, j) => j === i ? { ...x, score: Number(e.target.value) } : x))} />
                      <span className=ai-range-val>{s.score}</span>
                    </div>
                  ))}
                  <button className=ai-run-btn onClick={handlePathwayRecommend} disabled={pathwayLoading}>
                    {pathwayLoading ? '분석 중…' : '경로 추천 실행'}
                  </button>
                  {pathwayError && <p className=ai-error>{pathwayError}</p>}
                </div>
              </section>

              {pathwayResult ? (
                <section className=ai-panel>
                  <header className=ai-panel-head><span className=ai-panel-kicker>Result</span><h2 className=ai-panel-title>추천 학습 경로</h2></header>
                  <div className=ai-panel-body>
                    <p className=ai-summary-text>{pathwayResult.summary as string}</p>
                    <p className=ai-meta>총 예상 기간: {pathwayResult.totalEstimatedWeeks as number}주 ,  목표: {pathwayResult.goal as string}</p>
                    {(pathwayResult.pathSteps as Array<Record<string, unknown>>).map((step) => (
                      <div key={step.rank as number} className=ai-resource-card>
                        <div className=ai-resource-header>
                          <span className=ai-resource-rank>#{step.rank as number}</span>
                          <strong className=ai-resource-title>{step.subject as string}</strong>
                          <span className={`ai-badge ai-badge--${(step.currentScore as number) < 60 ? 'error' : (step.currentScore as number) < 75 ? 'warn' : 'ok'}`}>
                            현재 {step.currentScore as number}점 → 목표 {Math.round(step.targetScore as number)}점
                          </span>
                        </div>
                        <p className=ai-resource-meta>주간 {step.weeklyHours as number}h ,  예상 {step.estimatedWeeks as number}주</p>
                        <p className=ai-resource-units>집중 단원: {(step.focusUnits as string[]).join(' → ')}</p>
                        <p className=ai-resource-tip>💡 {step.tip as string}</p>
                        <a className=ai-resource-link href={(step.publicResource as string).includes('EBS') ? 'https://www.ebs.co.kr' : 'https://www.kmooc.kr'} target=_blank rel=noreferrer>
                          📚 {step.publicResource as string} (무료)
                        </a>
                      </div>
                    ))}
                  </div>
                </section>
              ) : (
                <HelpPanel title=학습 경로 가이드 items={[
                  { term: '취약도 = (100 - 점수) × 중요도', meaning: '점수가 낮고 중요도가 높은 과목이 우선 배치됩니다.' },
                  { term: '집중 단원', meaning: '국가 교육과정 단원 구조 기반으로 선행 단원부터 제시합니다.' },
                  { term: '공공 자원', meaning: 'EBS, K-MOOC 등 무료 공공 학습 자원만 연결합니다.' },
                ]} />
              )}
            </div>
          ) : null}

          {/* ── 조기 경보 탭 ─────────────────────────── */}
          {tab === 'warning' ? (
            <div className=ai-panel-grid>
              <section className=ai-panel>
                <header className=ai-panel-head><span className=ai-panel-kicker>Early Warning</span><h2 className=ai-panel-title>조기 경보 시스템</h2></header>
                <div className=ai-panel-body>
                  <p className=ai-sublabel>최근 성적 (최대 5개, 쉼표 구분)</p>
                  <input className=ai-text-input type=text
                    value={warningScores.join(', ')}
                    onChange={(e) => {
                      const nums = e.target.value.split(',').map((s) => Number(s.trim())).filter((n) => !isNaN(n) && n >= 0)
                      if (nums.length > 0) setWarningScores(nums)
                    }} />
                  {[
                    { label: '출결률 (%)', val: warningAttendance, set: setWarningAttendance },
                    { label: '과제 제출률 (%)', val: warningSubmission, set: setWarningSubmission },
                    { label: '수업 참여도 (%)', val: warningEngagement, set: setWarningEngagement },
                  ].map(({ label, val, set }) => (
                    <div key={label} className=ai-row-inline>
                      <span className=ai-row-label>{label}</span>
                      <input className=ai-range type=range min={0} max={100} value={val}
                        onChange={(e) => set(Number(e.target.value))} />
                      <span className=ai-range-val>{val}</span>
                    </div>
                  ))}
                  <button className=ai-run-btn onClick={handleWarningCheck} disabled={warningLoading}>
                    {warningLoading ? '분석 중…' : '위험 수준 진단'}
                  </button>
                  {warningError && <p className=ai-error>{warningError}</p>}
                </div>
              </section>

              {warningResult ? (
                <section className=ai-panel>
                  <header className=ai-panel-head><span className=ai-panel-kicker>Diagnosis</span><h2 className=ai-panel-title>경보 결과</h2></header>
                  <div className=ai-panel-body>
                    <div className={`ai-warning-badge ai-warning-badge--${warningResult.level as string}`}>
                      위험 수준: {(warningResult.level as string).toUpperCase()} ,  지수 {warningResult.riskScore as number}/100
                    </div>
                    <p className=ai-summary-text>{warningResult.summary as string}</p>
                    <p className=ai-meta>평균 성적 {warningResult.avgScore as number}점 ,  추세 {(warningResult.trend as number) >= 0 ? '+' : ''}{warningResult.trend as number}점</p>
                    <p className=ai-sublabel>트리거 요인</p>
                    <ul className=ai-list>
                      {(warningResult.triggers as string[]).map((t, i) => <li key={i} className=ai-list-item ai-list-item--warn>⚠️ {t}</li>)}
                    </ul>
                    <p className=ai-sublabel>권장 조치</p>
                    <ul className=ai-list>
                      {(warningResult.recommendedActions as string[]).map((a, i) => <li key={i} className=ai-list-item>→ {a}</li>)}
                    </ul>
                  </div>
                </section>
              ) : (
                <HelpPanel title=조기 경보 가이드 items={[
                  { term: '위험 수준 HIGH', meaning: '즉각적인 교사, 상담 개입이 필요한 상태입니다.', tip: '성적 하락 + 출결 저조가 겹치면 HIGH로 분류됩니다.' },
                  { term: '추세 (Trend)', meaning: '가장 오래된 점수와 최신 점수의 차이입니다. 음수면 하락입니다.' },
                  { term: '참여도', meaning: '수업 중 발언, 질문 횟수 등을 0~100으로 자체 평가합니다.' },
                ]} />
              )}
            </div>
          ) : null}

          {/* ── 형평성 지수 탭 ───────────────────────── */}
          {tab === 'equity' ? (
            <div className=ai-panel-grid>
              <section className=ai-panel>
                <header className=ai-panel-head><span className=ai-panel-kicker>Equity Index</span><h2 className=ai-panel-title>교육 형평성 지수</h2></header>
                <div className=ai-panel-body>
                  <label className=ai-label>지역
                    <select className=ai-select value={equityRegion} onChange={(e) => setEquityRegion(e.target.value)}>
                      {['전국','서울','경기','부산','인천','대구','광주','대전','전남','전북','경북','경남','충북','충남','강원','제주'].map((r) => <option key={r}>{r}</option>)}
                    </select>
                  </label>
                  <label className=ai-label>학교급
                    <select className=ai-select value={equitySchoolType} onChange={(e) => setEquitySchoolType(e.target.value)}>
                      {['고등','중학','초등'].map((t) => <option key={t}>{t}</option>)}
                    </select>
                  </label>
                  <label className=ai-label>연도
                    <input className=ai-number type=number min={2020} max={2026} value={equityYear}
                      onChange={(e) => setEquityYear(Number(e.target.value))} />
                  </label>
                  <button className=ai-run-btn onClick={handleEquityFetch} disabled={equityLoading}>
                    {equityLoading ? '조회 중…' : '형평성 지수 분석'}
                  </button>
                  {equityError && <p className=ai-error>{equityError}</p>}
                </div>
              </section>

              {equityResult ? (
                <section className=ai-panel>
                  <header className=ai-panel-head><span className=ai-panel-kicker>Result</span><h2 className=ai-panel-title>{equityRegion} {equitySchoolType} 형평성</h2></header>
                  <div className=ai-panel-body>
                    <div className={`ai-equity-score ai-equity-score--${(equityResult.equityScore as number) >= 80 ? 'ok' : (equityResult.equityScore as number) >= 50 ? 'warn' : 'error'}`}>
                      {equityResult.equityScore as number}<span className=ai-equity-unit>/100</span>
                      <span className=ai-equity-grade>{equityResult.grade as string}</span>
                    </div>
                    <p className=ai-summary-text>{equityResult.summary as string}</p>
                    {(() => {
                      const m = equityResult.metrics as Record<string, number>
                      const vn = equityResult.vsNational as Record<string, number>
                      return (
                        <>
                          <div className=ai-metrics-row>
                            {[
                              { label: '평균 성취도', val: m.averageScore, unit: '점' },
                              { label: '성취도 격차', val: m.achievementGap, unit: '점' },
                              { label: '교육 자원 지수', val: m.resourceIndex, unit: '' },
                              { label: '인프라 지수', val: m.infraIndex, unit: '' },
                            ].map(({ label, val, unit }) => (
                              <div key={label} className=ai-metric-cell>
                                <span className=ai-metric-label>{label}</span>
                                <span className=ai-metric-val>{val}{unit}</span>
                              </div>
                            ))}
                          </div>
                          <p className=ai-meta>전국 대비 성취도 {vn.avgDiff >= 0 ? '+' : ''}{vn.avgDiff}점 ,  형평성 {vn.equityDiff >= 0 ? '+' : ''}{vn.equityDiff}</p>
                        </>
                      )
                    })()}
                    <p className=ai-sublabel>정책 권고</p>
                    <ul className=ai-list>
                      {(equityResult.recommendations as string[]).map((r, i) => <li key={i} className=ai-list-item>→ {r}</li>)}
                    </ul>
                  </div>
                </section>
              ) : (
                <HelpPanel title=형평성 지수 가이드 items={[
                  { term: '형평성 점수 (0~100)', meaning: '격차가 작고 자원, 인프라가 풍부할수록 높습니다.' },
                  { term: '성취도 격차', meaning: '상위 집단과 하위 집단 간 평균 점수 차이입니다.' },
                  { term: '공공 데이터 연계', meaning: 'KESS 교육통계 API 연동 시 실데이터로 자동 교체됩니다.' },
                ]} />
              )}
            </div>
          ) : null}

          {/* ── 자원 매칭 탭 ─────────────────────────── */}
          {tab === 'resources' ? (
            <div className=ai-panel-grid>
              <section className=ai-panel>
                <header className=ai-panel-head><span className=ai-panel-kicker>Resource Matching</span><h2 className=ai-panel-title>공공 학습 자원 매칭</h2></header>
                <div className=ai-panel-body>
                  <label className=ai-label>과목
                    <select className=ai-select value={resourceSubject} onChange={(e) => setResourceSubject(e.target.value)}>
                      {['수학','영어','국어','과학','사회'].map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </label>
                  <div className=ai-row-inline>
                    <span className=ai-row-label>현재 성취도</span>
                    <input className=ai-range type=range min={0} max={100} value={resourceLevel}
                      onChange={(e) => setResourceLevel(Number(e.target.value))} />
                    <span className=ai-range-val>{resourceLevel}점</span>
                  </div>
                  <label className=ai-label>선호 형식
                    <select className=ai-select value={resourceFormat} onChange={(e) => setResourceFormat(e.target.value)}>
                      <option value=>전체</option>
                      <option value=video>동영상</option>
                      <option value=mooc>MOOC</option>
                      <option value=library>도서관</option>
                    </select>
                  </label>
                  <button className=ai-run-btn onClick={handleResourceMatch} disabled={resourceLoading}>
                    {resourceLoading ? '매칭 중…' : '자원 추천 실행'}
                  </button>
                  {resourceError && <p className=ai-error>{resourceError}</p>}
                </div>
              </section>

              {resourceResult ? (
                <section className=ai-panel>
                  <header className=ai-panel-head><span className=ai-panel-kicker>Matched</span><h2 className=ai-panel-title>추천 자원 {resourceResult.matchedCount as number}개</h2></header>
                  <div className=ai-panel-body>
                    <p className=ai-summary-text>{resourceResult.summary as string}</p>
                    {(resourceResult.resources as Array<Record<string, unknown>>).map((r, i) => (
                      <div key={i} className=ai-resource-card>
                        <div className=ai-resource-header>
                          <span className=ai-badge ai-badge--ok>{r.cost as string}</span>
                          <strong className=ai-resource-title>{r.title as string}</strong>
                        </div>
                        <p className=ai-resource-meta>유형: {r.type as string} ,  난이도: {r.difficulty as string}</p>
                        <a className=ai-resource-link href={r.url as string} target=_blank rel=noreferrer>
                          🔗 바로가기
                        </a>
                      </div>
                    ))}
                  </div>
                </section>
              ) : (
                <HelpPanel title=자원 매칭 가이드 items={[
                  { term: 'EBS 무료 강좌', meaning: '수능, 내신 대비 공식 콘텐츠로 전 과목 무료 제공합니다.' },
                  { term: 'K-MOOC', meaning: '국내 대학 강의를 무료로 수강할 수 있는 공공 플랫폼입니다.' },
                  { term: 'KOCW', meaning: '대학 개방 강의 포털. 심화 학습에 적합합니다.' },
                  { term: '매칭 기준', meaning: '현재 수준에서 ±15점 범위의 자원을 우선 추천합니다.' },
                ]} />
              )}
            </div>
          ) : null}

          {/* ── 자연어 데이터 질의 탭 ───────────────── */}
          {tab === 'nlq' ? (
            <div className=ai-panel-grid ai-panel-grid--full>
              <section className=ai-panel ai-panel--wide>
                <header className=ai-panel-head><span className=ai-panel-kicker>NLQ ,  Natural Language Query</span><h2 className=ai-panel-title>데이터 자연어 질의</h2></header>
                <div className=ai-panel-body>
                  <p className=ai-sublabel>교육 데이터에 대해 자연어로 질문하세요. 복잡한 쿼리 없이 인사이트를 얻을 수 있습니다.</p>
                  <div className=ai-nlq-chips>
                    {[
                      '수학 성적이 낮은 학생의 주요 위험 요인은?',
                      '서울과 전남의 교육 격차가 큰 이유는?',
                      '영어 70점 학생에게 맞는 공부 순서를 알려줘',
                      '출결률이 낮은 학생은 어떤 개입이 효과적인가?',
                    ].map((q) => (
                      <button key={q} className=ai-chip type=button onClick={() => setNlqInput(q)}>{q}</button>
                    ))}
                  </div>
                  <form className=ai-chat-form onSubmit={handleNlqSubmit}>
                    <textarea
                      className=ai-input
                      placeholder=예) 3학년 2반 수학 성적이 지난 달보다 낮아졌는데 원인이 뭘까요?
                      value={nlqInput}
                      onChange={(e) => setNlqInput(e.target.value)}
                      rows={2}
                    />
                    <button type=submit className=ai-send-btn disabled={nlqLoading || !nlqInput.trim()}>
                      {nlqLoading ? '분석 중…' : '질의'}
                    </button>
                  </form>
                  {nlqError && <p className=ai-error>{nlqError}</p>}
                </div>
              </section>

              {nlqResult ? (
                <section className=ai-panel ai-panel--wide>
                  <header className=ai-panel-head>
                    <span className=ai-panel-kicker>Domain: {nlqResult.domain as string}</span>
                    <h2 className=ai-panel-title>{nlqResult.intent as string}</h2>
                    {nlqResult.simulation ? <span className=ai-badge ai-badge--warn>시뮬레이션</span> : <span className=ai-badge ai-badge--ok>Live</span>}
                  </header>
                  <div className=ai-panel-body>
                    <div className=ai-nlq-answer>{nlqResult.answer as string}</div>
                    {Object.keys((nlqResult.keyEntities as Record<string, string>) ?? {}).filter((k) => (nlqResult.keyEntities as Record<string, string>)[k]).length > 0 ? (
                      <div className=ai-nlq-entities>
                        {Object.entries((nlqResult.keyEntities as Record<string, string>)).filter(([, v]) => v).map(([k, v]) => (
                          <span key={k} className=ai-chip ai-chip--entity>{k}: {v}</span>
                        ))}
                      </div>
                    ) : null}
                    {(nlqResult.suggestedActions as string[])?.length > 0 ? (
                      <>
                        <p className=ai-sublabel>다음 단계</p>
                        <ul className=ai-list>
                          {(nlqResult.suggestedActions as string[]).map((a, i) => <li key={i} className=ai-list-item>→ {a}</li>)}
                        </ul>
                      </>
                    ) : null}
                  </div>
                </section>
              ) : null}

              {nlqHistory.length > 0 ? (
                <section className=ai-panel ai-panel--wide>
                  <header className=ai-panel-head><span className=ai-panel-kicker>History</span><h2 className=ai-panel-title>최근 질의 내역</h2></header>
                  <div className=ai-panel-body>
                    {nlqHistory.map(({ query, result }, i) => (
                      <div key={i} className=ai-nlq-history-item>
                        <span className=ai-badge>{result.domain as string}</span>
                        <span className=ai-nlq-history-q>{query}</span>
                        <span className=ai-nlq-history-a>{(result.answer as string).slice(0, 80)}…</span>
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
          ) : null}

          </main>
        </div>
      </div>
    </div>
  )
}
