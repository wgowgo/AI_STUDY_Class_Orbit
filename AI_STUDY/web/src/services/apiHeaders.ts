function internalApiKey(): string {
  return (import.meta.env.VITE_INTERNAL_API_KEY ?? '').trim()
}

/** JSON POST 등에 Content-Type 과 내부 API 키를 함께 붙입니다. */
export function apiJsonHeaders(): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const key = internalApiKey()
  if (key) headers['X-Internal-Key'] = key
  return headers
}

/** multipart/form-data 등 Content-Type 을 직접 두는 요청용. */
export function apiAuthHeaders(): HeadersInit {
  const key = internalApiKey()
  return key ? { 'X-Internal-Key': key } : {}
}
