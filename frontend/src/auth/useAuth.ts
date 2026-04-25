import { getAccessToken, redirectToLogin } from './cognito'

export function useAuth() {
  const token = getAccessToken()
  const isAuthenticated = token !== null

  function requireAuth() {
    if (!isAuthenticated) redirectToLogin()
  }

  return { isAuthenticated, token, requireAuth }
}
