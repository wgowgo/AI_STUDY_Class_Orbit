import type { ClassAnalysisInput } from './pipeline'

const EXPLAIN_WORDS = [
  '정리',
  '핵심',
  '개념',
  '이유',
  '공식',
  '원리',
  '따라서',
  'because',
  'therefore',
  'concept',
]

const CHAT_WORDS = ['농담', '잡담', '딴얘기', '잠깐', '쉬자', '웃음', 'ㅋㅋ', 'ㅎㅎ']

const QUESTION_WORDS = ['?', '질문', '이해', '왜', '어떻게', 'what', 'why', 'how']

const KEYWORDS = [
  '학습',
  '성적',
  '분석',
  '피드백',
  '예측',
  '복습',
  '전략',
  '수업',
  '위험도',
  'time',
  'model',
]

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v))
}

function countMatches(text: string, words: string[]) {
  const lower = text.toLowerCase()
  return words.reduce((acc, w) => acc + (lower.match(new RegExp(w.toLowerCase(), 'g'))?.length ?? 0), 0)
}

export function deriveClassInputFromTranscript(transcript: string): {
  input: ClassAnalysisInput
  meta: {
    sentenceCount: number
    questionCount: number
    repeatedSentenceCount: number
  }
} {
  const clean = transcript.trim()
  const sentences = clean
    .split(/[.!?\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  const sentenceCount = Math.max(sentences.length, 1)

  const questionCount = countMatches(clean, QUESTION_WORDS)
  const explainCount = countMatches(clean, EXPLAIN_WORDS)
  const chatCount = countMatches(clean, CHAT_WORDS)
  const keywordCount = countMatches(clean, KEYWORDS)

  const normalized = sentences.map((s) => s.replace(/\s+/g, ' ').toLowerCase())
  const seen = new Set<string>()
  let repeatedSentenceCount = 0
  for (const s of normalized) {
    if (seen.has(s)) repeatedSentenceCount += 1
    seen.add(s)
  }

  const explanationFocus = clamp(
    Math.round(((explainCount + sentenceCount * 0.65) / (chatCount + sentenceCount)) * 100),
    25,
    95,
  )
  const questionPromptRate = clamp(Math.round((questionCount / sentenceCount) * 100), 0, 100)
  const keywordDensity = clamp(Math.round((keywordCount / sentenceCount) * 100), 5, 100)

  return {
    input: {
      transcriptLength: clean.length,
      explanationFocus,
      repetitionCount: repeatedSentenceCount,
      questionPromptRate,
      keywordDensity,
    },
    meta: {
      sentenceCount,
      questionCount,
      repeatedSentenceCount,
    },
  }
}
