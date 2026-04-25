import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { parseTokensFromHash, storeTokens } from '@/auth/cognito'

// Handles two redirects that land on /auth/callback:
//   1. Cognito hosted UI  → URL hash contains #access_token=...&id_token=...
//   2. bunq OAuth         → URL query contains ?bunq_state=...
//
// Both are handled in sequence if needed (Cognito first, bunq second).

export function AuthCallbackRoute() {
  const navigate       = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    // 1. Cognito tokens in the hash fragment
    const tokens = parseTokensFromHash()
    if (tokens) {
      storeTokens(tokens)
      window.history.replaceState(null, '', window.location.pathname)
    }

    // 2. bunq OAuth state returned as a query param
    const bunqState = searchParams.get('bunq_state')
    if (bunqState) {
      // Restore the onboarding form state from localStorage and continue.
      const savedState = localStorage.getItem('bunq_nest.onboard_state')
      if (savedState) {
        const parsed = JSON.parse(savedState)
        localStorage.setItem(
          'bunq_nest.onboard_state',
          JSON.stringify({ ...parsed, bunqOauthState: bunqState }),
        )
        navigate('/onboard', { replace: true })
        return
      }
    }

    // If only Cognito tokens were present, go to /chat or /onboard.
    if (tokens) {
      // The backend will tell us whether the user is onboarded.
      // For now, redirect to /onboard as a safe default.
      navigate('/onboard', { replace: true })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex h-screen items-center justify-center text-text-secondary text-sm">
      Signing you in…
    </div>
  )
}
