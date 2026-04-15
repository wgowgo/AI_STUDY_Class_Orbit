const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function transcribeAudio(file: File, language?: string) {
  const form = new FormData()
  form.append('file', file)
  if (language?.trim()) form.append('language', language.trim())

  const res = await fetch(`${API_BASE}/api/stt/transcribe`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status} ${text.slice(0, 200)}`)
  }

  return res.json() as Promise<{ transcript: string; model: string }>
}

