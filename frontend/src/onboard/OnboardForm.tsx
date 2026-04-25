import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PayslipUpload } from './PayslipUpload'
import { FundaInput } from './FundaInput'
import { submitOnboard } from '@/api/onboard'

type FormState = {
  s3Key?: string
  fundaUrl?: string
  fundaPriceOverride?: number
}

type StepState = 'done' | 'active' | 'pending'

function StepIndicator({ n, state }: { n: number; state: StepState }) {
  if (state === 'done') return (
    <div style={{
      width: 28, height: 28, borderRadius: 999, flexShrink: 0,
      background: 'var(--bunq-teal)', color: '#06222a',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 0 0 4px rgba(30,200,200,0.12)',
    }}>
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path d="M2.5 6.5L4.8 8.8L9.5 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
  if (state === 'active') return (
    <div style={{
      width: 28, height: 28, borderRadius: 999, flexShrink: 0,
      background: 'transparent', border: '1.5px solid var(--bunq-teal)',
      color: 'var(--bunq-teal)',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 13, fontWeight: 600,
      boxShadow: '0 0 0 4px rgba(30,200,200,0.12)',
    }}>{n}</div>
  )
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 999, flexShrink: 0,
      background: 'var(--surface-2)', border: '1px solid var(--surface-3)',
      color: 'var(--text-disabled)',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 13, fontWeight: 600,
    }}>{n}</div>
  )
}

function StepRow({ n, title, subtitle, state, children }: {
  n: number; title: string; subtitle: string; state: StepState; children?: React.ReactNode
}) {
  return (
    <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <StepIndicator n={n} state={state} />
        <div style={{
          flex: 1, width: 1.5, minHeight: 24, marginTop: 6,
          background: state === 'done' ? 'var(--bunq-teal)' : 'var(--surface-3)',
          opacity: state === 'done' ? 0.4 : 1,
        }} />
      </div>
      <div style={{ flex: 1, paddingBottom: 24, minWidth: 0 }}>
        <div style={{
          fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em',
          color: state === 'pending' ? 'var(--text-secondary)' : 'var(--text-primary)',
        }}>{title}</div>
        <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 2, lineHeight: 1.45 }}>
          {subtitle}
        </div>
        {children && <div style={{ marginTop: 12 }}>{children}</div>}
      </div>
    </div>
  )
}

export function OnboardForm() {
  const navigate = useNavigate()
  const [form, setForm]         = useState<FormState>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const step2State: StepState = !form.s3Key
    ? 'pending'
    : FUNDA_LISTING_REGEX.test(form.fundaUrl ?? '') ? 'done' : 'active'

  const canSubmit = !!form.s3Key && FUNDA_LISTING_REGEX.test(form.fundaUrl ?? '')

  async function handleSubmit() {
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await submitOnboard({
        s3_key:                   form.s3Key!,
        funda_url:                form.fundaUrl!,
        funda_price_override_eur: form.fundaPriceOverride,
      })
      navigate(`/chat?bootstrap=${res.session_id}`, { state: { profile: res.profile } })
    } catch {
      setError('Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <div style={{
      minHeight: '100svh',
      background: 'var(--surface-0)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Logo */}
      <div style={{ padding: '16px 24px 4px' }}>
        <img
          src="/bunq-logo.svg"
          alt="bunq"
          style={{ height: 22, width: 'auto', filter: 'invert(1) brightness(1.1)' }}
        />
      </div>

      {/* Heading */}
      <div style={{ padding: '16px 24px 20px' }}>
        <div className="t-caption" style={{ color: 'var(--bunq-teal)', marginBottom: 6 }}>Set up · 2 steps</div>
        <div className="t-display" style={{ fontSize: 24, lineHeight: 1.2 }}>
          Two things and<br />we're tracking.
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.5 }}>
          We use these to set a realistic target and check in on your progress.
        </div>
      </div>

      {/* Steps */}
      <div style={{ flex: 1, padding: '0 24px', overflow: 'auto' }}>
        <StepRow
          n={1} state={form.s3Key ? 'done' : 'active'}
          title="Upload your payslip"
          subtitle="One recent payslip is enough. We read income, taxes, and pension contributions."
        >
          <PayslipUpload onComplete={(s3Key) => setForm((f) => ({ ...f, s3Key }))} />
        </StepRow>

        <StepRow
          n={2} state={step2State}
          title="Add a Funda listing"
          subtitle="Doesn't need to be the one — just a price point you're aiming for."
        >
          {form.s3Key && (
            <FundaInput
              value={form.fundaUrl ?? ''}
              onChange={(fundaUrl, fundaPriceOverride) =>
                setForm((f) => ({ ...f, fundaUrl, fundaPriceOverride }))
              }
            />
          )}
        </StepRow>
      </div>

      {/* CTA */}
      <div style={{
        padding: '14px 20px 28px',
        borderTop: '1px solid var(--surface-3)',
        background: 'var(--surface-0)',
        display: 'flex', flexDirection: 'column', gap: 10,
        flexShrink: 0,
      }}>
        <button
          className="btn btn-primary"
          disabled={!canSubmit || submitting}
          onClick={handleSubmit}
          style={{ width: '100%', height: 48, borderRadius: 12, fontSize: 15 }}
        >
          {submitting ? 'Preparing your plan…' : 'Build my plan'}
          {!submitting && (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
            </svg>
          )}
        </button>
        {error && <div style={{ fontSize: 12.5, color: 'var(--error)', textAlign: 'center' }}>{error}</div>}
        <div style={{ fontSize: 11.5, color: 'var(--text-disabled)', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
            <path d="M9.5 5.5V4a3.5 3.5 0 0 0-7 0v1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" fill="none" />
            <rect x="2" y="5.5" width="8" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.2" fill="none" />
          </svg>
          Bank-grade encryption · we never store originals
        </div>
      </div>
    </div>
  )
}

const FUNDA_LISTING_REGEX = /^https:\/\/(www\.)?funda\.nl\/(detail\/)?(koop|huur|nieuwbouw)\//
