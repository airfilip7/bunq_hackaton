import { Button } from '@/components/ui/button'

// The bunq OAuth URL is provided by the backend env; frontend just redirects.
const BUNQ_OAUTH_URL = import.meta.env.VITE_BUNQ_OAUTH_URL as string

type Props = {
  onSkip?: () => void   // demo/mock mode only
}

export function BunqConnect({ onSkip }: Props) {
  function handleConnect() {
    // Persist form state before we leave the page.
    const state = localStorage.getItem('bunq_nest.onboard_state')
    if (!state) {
      console.warn('BunqConnect: no onboard_state in localStorage to preserve')
    }
    window.location.href = BUNQ_OAUTH_URL
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-text-secondary">
        Connect your bunq account so we can read your transactions and savings buckets.
        You'll be redirected to bunq and brought straight back.
      </p>
      <Button
        onClick={handleConnect}
        className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90 w-full"
      >
        Connect bunq
      </Button>
      {onSkip && (
        <button
          type="button"
          className="text-xs text-text-disabled underline"
          onClick={onSkip}
        >
          Skip (demo mode)
        </button>
      )}
    </div>
  )
}
