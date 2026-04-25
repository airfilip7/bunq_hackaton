// Thin fetch wrapper. No auth — bunq Nest runs inside the bunq app where
// identity is provided by the host. For the demo, the backend trusts the
// caller (single hard-coded user).

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('X-Dev-User-Id', 'u_demo')
  headers.set('Authorization', 'Bearer demo')
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}
