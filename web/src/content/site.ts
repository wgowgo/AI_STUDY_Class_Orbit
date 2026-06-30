export const NAV = [
  { id: 'intro', label: 'Intro' },
  { id: 'features', label: 'Features' },
  { id: 'flow', label: 'Flow' },
  { id: 'contact', label: 'Contact' },
] as const

export type NavId = (typeof NAV)[number]['id']

export const FEATURES = [
  {
    title: '수업 분석',
    body: 'STT / LLM으로 설명 비율, 반복, 질문 유도를 정량화합니다.',
    labelEn: 'Class analytics',
  },
  {
    title: '격차 예측',
    body: '성적, 출결, 수업 품질, 학교 환경을 묶어 위험도를 예측합니다.',
    labelEn: 'Gap & risk',
  },
  {
    title: '시간표 최적화',
    body: '상태–행동–보상 구조로 개인 맞춤 학습 배분을 탐색합니다.',
    labelEn: 'Schedule RL',
  },
  {
    title: '디지털 트윈',
    body: '적용 전 시나리오를 시뮬해 성적, 이해도 변화를 미리 봅니다.',
    labelEn: 'Digital twin',
  },
  {
    title: '인과 / 설명',
    body: 'SHAP 등으로 “왜 이런 결과인지”를 사람이 읽을 수 있게 합니다.',
    labelEn: 'Causal explain',
  },
  {
    title: '학습 경로 엔진',
    body: '과목별 취약도를 분석해 최적 학습 순서와 공공 자원 연결을 제안합니다.',
    labelEn: 'Learning pathway',
  },
  {
    title: '조기 경보',
    body: '성적 추이, 출결, 참여도를 종합해 위험 학생을 사전에 감지합니다.',
    labelEn: 'Early warning',
  },
  {
    title: '형평성 지수',
    body: '지역, 학교급별 교육 격차를 수치화해 정책 의사결정을 지원합니다.',
    labelEn: 'Equity index',
  },
  {
    title: '자원 매칭',
    body: 'EBS, K-MOOC 등 무료 공공 학습 자원을 수준에 맞춰 자동 추천합니다.',
    labelEn: 'Resource match',
  },
  {
    title: '자연어 질의',
    body: '복잡한 쿼리 없이 자연어로 교육 데이터에 대해 질문하고 인사이트를 얻습니다.',
    labelEn: 'NLQ',
  },
] as const

export const STAT_ROWS: readonly [string, string][] = [
  ['01', '수업 분석 → 품질 지표'],
  ['02', '학생 / 환경 → 위험 예측'],
  ['03', '전략 → 트윈 검증 → 재학습'],
]

export const FLOW_STEPS = [
  '공공 API → 전처리',
  'ML 위험도',
  'RL / 규칙 시간표',
  'LLM 수업 피드백',
  'SHAP 설명',
  'UI, API',
] as const

/** 투어 리스트에서 영어 포인트 강조용 (FLOW_STEPS와 동일 순서) */
export const FLOW_STEPS_EN = [
  'Ingest, prep',
  'ML risk score',
  'RL / rules',
  'LLM feedback',
  'SHAP explain',
  'UI, API',
] as const
