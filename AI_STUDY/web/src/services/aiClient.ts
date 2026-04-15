export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  role: ChatRole
  content: string
}

type ChatApiResponse = {
  answer?: string
  message?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const DEFAULT_API_URL = `${API_BASE}/api/ai/chat`

function makeFallbackAnswer(input: string) {
  return [
    '실제 AI 서버 연결 전 임시 응답입니다.',
    `질문 요약: ${input.slice(0, 80)}${input.length > 80 ? '...' : ''}`,
    '서버를 연결하려면 VITE_AI_API_URL 또는 /api/ai/chat 엔드포인트를 사용하세요.',
  ].join('\n')
}

export type AskAiResult = {
  answer: string
  /** 서버 `/api/ai/chat` 응답이면 live, 네트워크/오류 시 브라우저 폴백이면 local */
  source: 'live' | 'local'
}

export async function askAi(message: string, history: ChatMessage[]): Promise<AskAiResult> {
  const apiUrl = import.meta.env.VITE_AI_API_URL ?? DEFAULT_API_URL

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = (await response.json()) as ChatApiResponse
    const answer = (data.answer ?? data.message ?? '').trim()
    if (!answer) throw new Error('empty response')
    return { answer, source: 'live' }
  } catch {
    return { answer: makeFallbackAnswer(message), source: 'local' }
  }
}
