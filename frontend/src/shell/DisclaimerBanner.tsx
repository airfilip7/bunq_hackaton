import { useState } from 'react'

const DISMISSED_KEY = 'bunq_nest.disclaimer_dismissed'

export function DisclaimerBanner() {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === 'true',
  )

  if (dismissed) return null

  return (
    <div className="w-full bg-surface-1 border-b border-surface-3 px-4 py-2 flex items-center justify-between gap-4 text-xs text-text-secondary">
      <span>
        bunq Nest helps you prepare for homeownership. It is not mortgage advice.
        When you're ready to apply, bunq connects you with licensed advisors.
      </span>
      <button
        className="shrink-0 text-text-disabled hover:text-text-secondary"
        onClick={() => {
          localStorage.setItem(DISMISSED_KEY, 'true')
          setDismissed(true)
        }}
      >
        ✕
      </button>
    </div>
  )
}
