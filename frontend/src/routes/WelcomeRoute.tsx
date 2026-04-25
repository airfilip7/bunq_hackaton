import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// ─── Coach preview hero ───────────────────────────────────────────────────────

const COACH_LINES = [
  'You can save €640/mo without lifestyle changes.',
  'If we shift €200 from Buffer → House, you close the gap by July.',
  'Heads up — your dining-out spend is up €78 vs last month.',
  'You crossed 50% of your deposit goal. Nice.',
]

function HeroCoach() {
  const [idx, setIdx] = useState(0)
  const [chars, setChars] = useState(0)

  useEffect(() => {
    const line = COACH_LINES[idx]
    if (chars < line.length) {
      const t = setTimeout(() => setChars(chars + 1), 18)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => {
      setChars(0)
      setIdx((idx + 1) % COACH_LINES.length)
    }, 2200)
    return () => clearTimeout(t)
  }, [idx, chars])

  const text = COACH_LINES[idx].slice(0, chars)

  return (
    <div style={{
      width: '100%',
      borderRadius: 18,
      border: '1px solid var(--surface-3)',
      background: 'var(--surface-2)',
      padding: 18,
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      {/* Coach header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img
          src="/bunq-avatar.png"
          alt="bunq coach"
          style={{
            width: 36, height: 36, borderRadius: 999, objectFit: 'cover',
            boxShadow: '0 0 0 4px rgba(30,200,200,0.12)',
          }}
        />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>bunq Coach</div>
          <div style={{ fontSize: 10.5, color: 'var(--success)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--success)', display: 'inline-block' }} />
            online · checking your accounts
          </div>
        </div>
      </div>

      {/* Typing bubble */}
      <div style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--surface-3)',
        borderRadius: '14px 14px 14px 4px',
        padding: '12px 14px',
        fontSize: 13, lineHeight: 1.55, minHeight: 90,
      }}>
        {text}
        <span className="bunq-cursor" />
      </div>

      {/* Pagination dots */}
      <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
        {COACH_LINES.map((_, i) => (
          <div key={i} style={{
            width: i === idx ? 16 : 6, height: 6, borderRadius: 999,
            background: i === idx ? 'var(--bunq-teal)' : 'var(--surface-3)',
            transition: 'width 200ms',
          }} />
        ))}
      </div>
    </div>
  )
}

// ─── Welcome screen ───────────────────────────────────────────────────────────

export function WelcomeRoute() {
  const navigate  = useNavigate()
  const { search } = useLocation()  // preserve ?mock=1 / ?demo=1

  return (
    <div style={{
      minHeight: '100svh',
      background: 'var(--surface-0)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* bunq logo */}
      <div className="reveal" style={{ animationDelay: '60ms', padding: '16px 24px 4px' }}>
        <img
          src="/bunq-logo.svg"
          alt="bunq"
          style={{ height: 24, width: 'auto', filter: 'invert(1) brightness(1.1)' }}
        />
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '16px 24px 0', gap: 20, overflow: 'auto' }}>

        {/* Headline */}
        <div className="reveal" style={{ animationDelay: '160ms' }}>
          <div className="t-caption" style={{ color: 'var(--bunq-yellow)', marginBottom: 8, fontSize: 10 }}>
            The home-buying coach
          </div>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.05 }}>
            Your first home,<br />
            <span style={{ color: 'var(--bunq-teal)' }}>already within reach.</span>
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginTop: 10, lineHeight: 1.55 }}>
            We read the numbers, find the slack, and keep nudging until you've got the keys.
          </div>
        </div>

        {/* Hero */}
        <div className="reveal" style={{ animationDelay: '320ms' }}>
          <HeroCoach />
        </div>

        {/* Social proof */}
        <div className="reveal" style={{
          animationDelay: '480ms',
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 12px',
          background: 'var(--surface-2)',
          border: '1px solid var(--surface-3)',
          borderRadius: 12,
        }}>
          <div style={{ display: 'flex' }}>
            {['#1ec8c8', '#ffd72e', '#a78bfa'].map((c, i) => (
              <div key={i} style={{
                width: 22, height: 22, borderRadius: 999,
                background: c, border: '2px solid var(--surface-2)',
                marginLeft: i ? -8 : 0,
              }} />
            ))}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.35 }}>
            <strong style={{ color: 'var(--text-primary)' }}>2,400+</strong> bunqers saving for their first place
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="reveal" style={{
        animationDelay: '600ms',
        padding: '14px 24px 32px',
        flexShrink: 0,
      }}>
        <button
          className="btn btn-primary"
          style={{ width: '100%', height: 50, borderRadius: 14, fontSize: 15 }}
          onClick={() => navigate(`/onboard${search}`)}
        >
          Get started
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
    </div>
  )
}
