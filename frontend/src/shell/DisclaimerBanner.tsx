import { useState } from 'react'
import { Icon } from '@/components/Icon'

const DISMISSED_KEY = 'bunq_nest.disclaimer_dismissed'

export function DisclaimerBanner() {
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISSED_KEY) === 'true',
  )

  if (dismissed) return null

  return (
    <div style={{
      width: '100%', background: 'rgba(0,0,0,0.30)',
      borderBottom: '1px solid var(--line-2)',
      padding: '8px 16px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
      fontSize: 12, color: 'var(--ink-3)',
    }}>
      <span>
        bunq Nest helps you prepare for homeownership. It is not mortgage advice.
        When you're ready to apply, bunq connects you with licensed advisors.
      </span>
      <button
        onClick={() => {
          localStorage.setItem(DISMISSED_KEY, 'true')
          setDismissed(true)
        }}
        style={{ flexShrink: 0, color: 'var(--ink-4)', cursor: 'pointer' }}
      >
        <Icon name="x" size={14}/>
      </button>
    </div>
  )
}
