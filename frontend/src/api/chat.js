const BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function fetchWithTimeout(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timeoutId)
  }
}

function getAskBaseCandidates() {
  if (BASE_URL.startsWith('/')) {
    return [BASE_URL]
  }

  const bases = [BASE_URL, 'http://127.0.0.1:8000', 'http://localhost:8000']
  if (typeof window !== 'undefined' && window.location?.hostname) {
    bases.unshift(`http://${window.location.hostname}:8000`)
  }
  return [...new Set(bases.filter(Boolean))]
}

export async function askQuestion(question, sessionId) {
  let lastError = null

  for (const base of getAskBaseCandidates()) {
    try {
      const res = await fetchWithTimeout(`${base}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        const detail = data?.detail || `Ask failed: ${res.status} ${res.statusText}`
        throw new Error(detail)
      }

      return res.json()
    } catch (err) {
      lastError = err
      const isNetworkError = err?.name === 'AbortError' || err instanceof TypeError
      if (!isNetworkError) {
        throw err
      }
    }
  }

  throw new Error(`Failed to reach backend for /ask: ${lastError?.message || 'unknown error'}`)
}