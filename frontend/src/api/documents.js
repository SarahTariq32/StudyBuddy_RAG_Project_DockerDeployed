const ENV_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const API_BASE_STORAGE_KEY = 'rag_api_base'

// True when VITE_API_URL points at a real remote host (not localhost / 127.x).
// In this case we never try loopback addresses — they can never reach the backend.
const IS_REMOTE_ENV =
  ENV_BASE_URL &&
  !ENV_BASE_URL.includes('localhost') &&
  !ENV_BASE_URL.includes('127.0.0.1')

function getStoredApiBase() {
  try {
    return localStorage.getItem(API_BASE_STORAGE_KEY)
  } catch (_) {
    return null
  }
}

function storeApiBase(base) {
  try {
    localStorage.setItem(API_BASE_STORAGE_KEY, base)
  } catch (_) {
    // Ignore storage errors (private mode / blocked storage).
  }
}

function clearStoredApiBase() {
  try {
    localStorage.removeItem(API_BASE_STORAGE_KEY)
  } catch (_) {
    // Ignore storage errors.
  }
}

function getApiBaseCandidates() {
  if (ENV_BASE_URL.startsWith('/')) {
    return [ENV_BASE_URL]
  }

  // In production (remote URL configured), only ever try the configured URL.
  // Trying localhost first would waste the timeout on every single request.
  if (IS_REMOTE_ENV) {
    const storedBase = getStoredApiBase()
    // Only use a stored base if it matches the configured remote (prevents
    // stale localhost entries from a previous local dev session).
    const validStored = storedBase && !storedBase.includes('localhost') && !storedBase.includes('127.0.0.1')
      ? storedBase
      : null
    return [...new Set([validStored, ENV_BASE_URL].filter(Boolean))]
  }

  // Local dev: try stored winner first, then loopback variants, then env URL.
  const storedBase = getStoredApiBase()
  const candidates = [storedBase, 'http://127.0.0.1:8000', ENV_BASE_URL, 'http://localhost:8000']

  if (typeof window !== 'undefined' && window.location?.hostname) {
    candidates.unshift(`http://${window.location.hostname}:8000`)
  }

  return [...new Set(candidates.filter(Boolean))]
}

function isLoopbackBase(base) {
  return base === 'http://127.0.0.1:8000' || base === 'http://localhost:8000'
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 1500) {
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

function isNetworkError(err) {
  return err?.name === 'AbortError' || err instanceof TypeError
}

async function requestWithBaseFallback(path, options = {}, timeoutMs = null) {
  let lastError = null

  for (const base of getApiBaseCandidates()) {
    try {
      const url = `${base}${path}`
      const res = timeoutMs == null
        ? await fetch(url, options)
        : await fetchWithTimeout(url, options, timeoutMs)

      storeApiBase(base)
      return res
    } catch (err) {
      if (!isNetworkError(err)) {
        throw err
      }
      lastError = err
    }
  }

  throw new Error(`Failed to reach backend on all base URLs: ${lastError?.message || 'unknown error'}`)
}

export async function listPDFs() {
  const res = await requestWithBaseFallback('/documents', { cache: 'no-store' }, 2500)
  if (!res.ok) {
    throw new Error(`Failed to load PDFs: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// export async function uploadPDF(file) {
//   const formData = new FormData()
//   formData.append('file', file)
//   const res = await fetch(`${BASE_URL}/documents`, {
//     method: 'POST',
//     body: formData,
//   })
//   return res.json()
// }

export async function uploadPDF(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await requestWithBaseFallback('/documents', {
    method: 'POST',
    body: formData,
  }, 30000)

  if (!res.ok) {
    let message = 'Upload failed'
    try {
      const data = await res.json()
      message = data?.detail || message
    } catch (_) {}
    throw new Error(message)
  }

  // In local dev, clear a stored loopback base after a successful upload so
  // the next request re-discovers the fastest candidate.
  if (!IS_REMOTE_ENV && isLoopbackBase(getStoredApiBase())) {
    clearStoredApiBase()
  }

  return res.json()
}

export async function deletePDF(id) {
  const res = await requestWithBaseFallback(`/documents/${id}`, { method: 'DELETE' }, 5000)
  if (!res.ok) {
    throw new Error(`Delete failed: ${res.status} ${res.statusText}`)
  }
}

// export async function renamePDF(id, filename) {
//   const payload = { filename }
//   let res = await fetch(`${BASE_URL}/documents/${id}`, {
//     method: 'PATCH',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify(payload),
//   })

//   // Support backends that use PUT for updates.
//   if (!res.ok && (res.status === 404 || res.status === 405)) {
//     res = await fetch(`${BASE_URL}/documents/${id}`, {
//       method: 'PUT',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify(payload),
//     })
//   }

//   if (!res.ok) {
//     throw new Error('Failed to rename PDF')
//   }

//   const contentType = res.headers.get('content-type') || ''
//   if (contentType.includes('application/json')) {
//     return res.json()
//   }

//   return null
// }


export async function renamePDF(id, filename) {
  const cleanName = filename.trim()

  const attempts = [
    { path: '/documents/' + id, method: 'PATCH', body: { filename: cleanName } },
    { path: '/documents/' + id, method: 'PATCH', body: { name: cleanName } },
    { path: '/documents/' + id, method: 'PUT', body: { filename: cleanName } },
    { path: '/documents/' + id, method: 'PUT', body: { name: cleanName } },
    { path: '/documents/' + id + '/rename', method: 'PATCH', body: { filename: cleanName } },
    { path: '/documents/' + id + '/rename', method: 'PATCH', body: { new_name: cleanName } },
    { path: '/documents/' + id + '/rename', method: 'PUT', body: { filename: cleanName } }
  ]

  for (const attempt of attempts) {
    const res = await requestWithBaseFallback(attempt.path, {
      method: attempt.method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(attempt.body)
    }, 5000)

    if (res.ok) {
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        return res.json()
      }
      return null
    }

    // Try next contract on common "wrong route/method" statuses.
    if (res.status !== 404 && res.status !== 405 && res.status !== 422) {
      const text = await res.text().catch(() => '')
      throw new Error('Rename failed: ' + res.status + ' ' + text)
    }
  }

  throw new Error('Rename failed: no matching backend rename contract found')
}