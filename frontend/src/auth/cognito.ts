// Cognito hosted UI helpers — full-redirect flow (no Amplify SDK needed).

const COGNITO_LOGIN_URL  = import.meta.env.VITE_COGNITO_LOGIN_URL as string
const COGNITO_LOGOUT_URL = import.meta.env.VITE_COGNITO_LOGOUT_URL as string

export function redirectToLogin() {
  window.location.href = COGNITO_LOGIN_URL
}

export function redirectToLogout() {
  window.location.href = COGNITO_LOGOUT_URL
}

// After the Cognito hosted UI redirect the URL contains id_token + access_token
// in the hash fragment (implicit grant) or a ?code= param (auth-code grant).
// We use the implicit grant for simplicity in the hackathon.
export function parseTokensFromHash(): { accessToken: string; idToken: string } | null {
  const hash = window.location.hash.slice(1)
  if (!hash) return null
  const params = new URLSearchParams(hash)
  const accessToken = params.get('access_token')
  const idToken     = params.get('id_token')
  if (!accessToken || !idToken) return null
  return { accessToken, idToken }
}

export function storeTokens(tokens: { accessToken: string; idToken: string }) {
  localStorage.setItem('bunq_nest.access_token', tokens.accessToken)
  localStorage.setItem('bunq_nest.id_token',     tokens.idToken)
}

export function getAccessToken(): string | null {
  return localStorage.getItem('bunq_nest.access_token')
}

export function clearTokens() {
  localStorage.removeItem('bunq_nest.access_token')
  localStorage.removeItem('bunq_nest.id_token')
}
