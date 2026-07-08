const BASE_URL = import.meta.env.VITE_API_URL || '/api'
const DASHBOARD_CACHE_KEY = 'studybuddy_ops_dashboard_cache'
const TRACES_CACHE_KEY = 'studybuddy_ops_traces_cache'

function readCache(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch (_) {
    return null
  }
}

function writeCache(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (_) {
    // Ignore storage failures.
  }
}

export function getCachedOpsDashboard() {
  return readCache(DASHBOARD_CACHE_KEY)
}

export function getCachedOpsTraces() {
  return readCache(TRACES_CACHE_KEY)
}

async function fetchWithTimeout(url, options = {}) {
  return fetch(url, {
    ...options,
    cache: 'no-store',
  })
}

function getBaseCandidates() {
  // When built for production (Docker), BASE_URL defaults to '/api'.
  // Use that relative path so nginx can proxy to the backend.
  if (BASE_URL && BASE_URL !== '/api') {
    return [BASE_URL];
  }
  return ['/api'];
}

function isTraceDetailPath(path) {
  return /^\/ops\/traces\/[^/?]+/.test(path)
}

function cacheKeyForPath(path) {
  if (isTraceDetailPath(path)) return null
  return path.startsWith('/ops/traces') ? TRACES_CACHE_KEY : DASHBOARD_CACHE_KEY
}

function emptyResponseForPath(path) {
  if (isTraceDetailPath(path)) {
    return { enabled: true, project: null, trace: null }
  }
  return path.startsWith('/ops/traces')
    ? { enabled: true, project: null, count: 0, traces: [] }
    : { enabled: true, project: null, metrics: {}, charts: {}, recent_requests: [] }
}

async function requestOps(path) {
  let lastError = null
  const cacheKey = cacheKeyForPath(path)

  for (const base of getBaseCandidates()) {
    try {
      const res = await fetchWithTimeout(`${base}${path}`)
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(`Ops API failed (${res.status}): ${text || res.statusText}`)
      }
      const data = await res.json()
      if (cacheKey) {
        writeCache(cacheKey, data)
      }
      return data
    } catch (err) {
      lastError = err
      const isNetworkError = err?.name === 'AbortError' || err instanceof TypeError
      if (!isNetworkError) {
        throw err
      }
    }
  }

  if (cacheKey) {
    const cached = readCache(cacheKey)
    if (cached) {
      return cached
    }
  } else if (isTraceDetailPath(path)) {
    const traceId = decodeURIComponent(path.split('/').pop() || '')
    const tracesCached = readCache(TRACES_CACHE_KEY)
    const fromList = tracesCached?.traces?.find?.(t => t?.id === traceId)
    if (fromList) {
      return { enabled: true, project: tracesCached?.project || null, trace: fromList }
    }
  }

  const isAbortLike = lastError?.name === 'AbortError' || String(lastError?.message || '').toLowerCase().includes('aborted')
  if (isAbortLike) {
    return emptyResponseForPath(path)
  }

  throw new Error(`Unable to fetch ops data: ${lastError?.message || 'unknown error'}`)
}

export function fetchOpsDashboard({ hours = 24, limit = 120 } = {}) {
  return requestOps(`/ops/dashboard?hours=${hours}&limit=${limit}`)
}

export function fetchOpsTraces({ hours = 24, limit = 40 } = {}) {
  return requestOps(`/ops/traces?hours=${hours}&limit=${limit}`)
}

export function fetchOpsTraceById(traceId) {
  return requestOps(`/ops/traces/${encodeURIComponent(traceId)}`)
}
