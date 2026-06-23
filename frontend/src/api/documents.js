const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function listPDFs() {
  const res = await fetch(`${BASE_URL}/documents`)
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

  const res = await fetch(`${BASE_URL}/documents`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    let message = 'Upload failed'
    try {
      const data = await res.json()
      message = data?.detail || message
    } catch (_) {}
    throw new Error(message)
  }

  return res.json()
}

export async function deletePDF(id) {
  await fetch(`${BASE_URL}/documents/${id}`, { method: 'DELETE' })
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
    { url: BASE_URL + '/documents/' + id, method: 'PATCH', body: { filename: cleanName } },
    { url: BASE_URL + '/documents/' + id, method: 'PATCH', body: { name: cleanName } },
    { url: BASE_URL + '/documents/' + id, method: 'PUT', body: { filename: cleanName } },
    { url: BASE_URL + '/documents/' + id, method: 'PUT', body: { name: cleanName } },
    { url: BASE_URL + '/documents/' + id + '/rename', method: 'PATCH', body: { filename: cleanName } },
    { url: BASE_URL + '/documents/' + id + '/rename', method: 'PATCH', body: { new_name: cleanName } },
    { url: BASE_URL + '/documents/' + id + '/rename', method: 'PUT', body: { filename: cleanName } }
  ]

  for (const attempt of attempts) {
    const res = await fetch(attempt.url, {
      method: attempt.method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(attempt.body)
    })

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