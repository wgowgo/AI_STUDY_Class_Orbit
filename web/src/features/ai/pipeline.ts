export type ClassAnalysisInput = {
  transcriptLength: number
  explanationFocus: number
  repetitionCount: number
  questionPromptRate: number
  keywordDensity: number
}

export type RiskInput = {
  averageScore: number
  attendanceRate: number
  classQualityScore: number
  schoolEnvironmentScore: number
}

export type ScheduleInput = {
  koreanLevel: number
  mathLevel: number
  englishLevel: number
  fatigue: number
  studyHours: number
}

export type TwinInput = {
  currentAverage: number
  planQuality: number
  consistency: number
  weeks: number
}

export type CausalInput = {
  attendanceImpact: number
  classQualityImpact: number
  selfStudyImpact: number
  environmentImpact: number
}

export type ExplainInput = {
  attendance: number
  understanding: number
  fatigue: number
  classQuality: number
}

const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v))

export function analyzeClass(input: ClassAnalysisInput) {
  const explanationRatio = clamp(input.explanationFocus / 100, 0, 1)
  const repetitionPenalty = clamp(input.repetitionCount / 30, 0, 1)
  const questionBoost = clamp(input.questionPromptRate / 100, 0, 1)
  const keywordBoost = clamp(input.keywordDensity / 100, 0, 1)

  const base =
    explanationRatio * 0.45 +
    (1 - repetitionPenalty) * 0.2 +
    questionBoost * 0.2 +
    keywordBoost * 0.15

  const volumePenalty = input.transcriptLength < 300 ? 0.07 : 0
  const score = clamp(Math.round((base - volumePenalty) * 100), 0, 100)

  return {
    qualityScore: score,
    explanationRatio: Math.round(explanationRatio * 100),
    repetitionCount: input.repetitionCount,
    questionPromptRate: input.questionPromptRate,
    keywordDensity: input.keywordDensity,
    feedback:
      score >= 80
        ? '설명 구조가 안정적입니다. 질문 유도 빈도를 현재 수준 이상 유지하세요.'
        : score >= 60
          ? '설명 밀도는 양호하지만 반복 구간이 길어집니다. 키워드 중심 정리를 늘려보세요.'
          : '설명 대비 잡담/반복 비율이 높습니다. 핵심 개념 중심으로 문장 길이를 줄이세요.',
  }
}

export function predictRisk(input: RiskInput) {
  const riskRaw =
    (100 - input.averageScore) * 0.4 +
    (100 - input.attendanceRate) * 0.3 +
    (100 - input.classQualityScore) * 0.2 +
    (100 - input.schoolEnvironmentScore) * 0.1

  const risk = clamp(Math.round(riskRaw), 0, 100)
  const dropoutProb = clamp(Math.round(risk * 0.72), 0, 100)

  return {
    subjectRisk: risk,
    dropoutProbability: dropoutProb,
    level: risk >= 70 ? 'high' : risk >= 40 ? 'medium' : 'low',
  }
}

export function optimizeSchedule(input: ScheduleInput) {
  const weakKorean = 100 - input.koreanLevel
  const weakMath = 100 - input.mathLevel
  const weakEnglish = 100 - input.englishLevel
  const totalWeak = Math.max(weakKorean + weakMath + weakEnglish, 1)

  const fatigueFactor = clamp(1 - input.fatigue / 140, 0.55, 1)
  const effectiveHours = Math.max(Math.round(input.studyHours * fatigueFactor * 10) / 10, 1)

  const koreanHours = Math.round(((weakKorean / totalWeak) * effectiveHours) * 10) / 10
  const mathHours = Math.round(((weakMath / totalWeak) * effectiveHours) * 10) / 10
  const englishHours =
    Math.round((Math.max(effectiveHours - koreanHours - mathHours, 0.5)) * 10) / 10

  return {
    effectiveHours,
    routine: [
      `국어 ${koreanHours}h (개념 + 오답)`,
      `수학 ${mathHours}h (유형 반복 + 약점 단원)`,
      `영어 ${englishHours}h (독해 + 단어 회전)`,
      '마감 20분: 오늘 학습 회고 및 내일 계획',
    ],
  }
}

export function simulateTwin(input: TwinInput) {
  const gainPerWeek =
    input.planQuality * 0.12 + input.consistency * 0.18 - (100 - input.currentAverage) * 0.02
  const predicted = clamp(Math.round(input.currentAverage + gainPerWeek * (input.weeks / 4)), 0, 100)
  const delta = predicted - input.currentAverage

  return {
    predictedAverage: predicted,
    delta,
    comment:
      delta >= 8
        ? '현재 전략은 유의미한 상승이 예상됩니다.'
        : delta >= 3
          ? '완만한 상승이 예상됩니다. 복습 비율을 더 높이면 개선 폭이 커집니다.'
          : '상승 폭이 제한적입니다. 시간표 재배분 또는 피로도 관리가 필요합니다.',
  }
}

export function analyzeCausal(input: CausalInput) {
  const items = [
    ['출결', input.attendanceImpact],
    ['수업 품질', input.classQualityImpact],
    ['자기주도 학습', input.selfStudyImpact],
    ['학교 환경', input.environmentImpact],
  ] as const

  const sorted = [...items].sort((a, b) => b[1] - a[1])
  const top = sorted[0]
  const second = sorted[1]

  return {
    topDriver: top[0],
    topWeight: top[1],
    summary: `${top[0]} 요인이 가장 큰 원인으로 추정됩니다. 다음 영향 요인은 ${second[0]}입니다.`,
    ranking: sorted,
  }
}

export function explainPrediction(input: ExplainInput) {
  const raw = {
    attendance: 100 - input.attendance,
    understanding: 100 - input.understanding,
    fatigue: input.fatigue,
    classQuality: 100 - input.classQuality,
  }

  const total = Math.max(raw.attendance + raw.understanding + raw.fatigue + raw.classQuality, 1)
  const pct = {
    attendance: Math.round((raw.attendance / total) * 100),
    understanding: Math.round((raw.understanding / total) * 100),
    fatigue: Math.round((raw.fatigue / total) * 100),
    classQuality: Math.round((raw.classQuality / total) * 100),
  }

  return pct
}
