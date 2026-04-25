// Thin fetch wrapper — injects the Cognito JWT on every request.

const API_BASE = import.meta.env.VITE_API_URL ?? ''

function getToken(): string | null {
  // Cognito hosted UI stores the access token in localStorage under a
  // CognitoIdentityServiceProvider.*.accessToken key. We resolve it lazily
  // so this file can be imported before auth is initialised.
  const key = Object.keys(localStorage).find(
    k => k.includes('accessToken') && k.includes('CognitoIdentityServiceProvider'),
  )
  return key ? (localStorage.getItem(key) ?? null) : null
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (res.status === 401) {
    // Token expired — redirect to Cognito hosted UI to refresh.
    window.location.href = `${import.meta.env.VITE_COGNITO_LOGIN_URL}`
  }

  return res
}
