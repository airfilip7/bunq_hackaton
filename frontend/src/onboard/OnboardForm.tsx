import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '@/components/Icon'
import { PayslipUpload } from './PayslipUpload'
import { FundaInput } from './FundaInput'
import { submitOnboard } from '@/api/onboard'
import type { PayslipUploadResult } from '@/api/types'

type FormState = {
  payslipResult?: PayslipUploadResult
  fundaUrl?: string
  fundaPriceOverride?: number
}

const FUNDA_LISTING_REGEX = /^https:\/\/(www\.)?funda\.nl\/(detail\/)?(koop|huur|nieuwbouw)\//

const us = {
  page: { minHeight: '100vh', padding: '32px 24px 80px', color: 'var(--ink)' } as React.CSSProperties,
  topbar: { maxWidth: 880, margin: '0 auto 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' } as React.CSSProperties,
  back: { display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--ink-3)', fontSize: 14, padding: '8px 12px', borderRadius: 999, cursor: 'pointer' } as React.CSSProperties,
  brand: { display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600, fontSize: 15 } as React.CSSProperties,
  brandMark: { width: 26, height: 26, borderRadius: 8, background: 'var(--rainbow)', color: 'white', display: 'grid', placeItems: 'center', fontFamily: 'var(--font-serif)', fontStyle: 'italic' as const, fontSize: 16 } as React.CSSProperties,
  card: { maxWidth: 880, margin: '0 auto', background: 'rgba(20,10,32,0.6)', borderRadius: 28, border: '1px solid var(--line)', overflow: 'hidden', backdropFilter: 'blur(20px)', boxShadow: 'var(--shadow-lg)' } as React.CSSProperties,
  header: { padding: '40px 48px 28px', background: 'linear-gradient(180deg, rgba(168,85,247,0.10), transparent)', borderBottom: '1px solid var(--line-2)', position: 'relative' as const } as React.CSSProperties,
  greet: { fontFamily: 'var(--font-serif)', fontSize: 38, lineHeight: 1.05, fontWeight: 400, letterSpacing: '-0.02em', margin: '0 0 10px' } as React.CSSProperties,
  greetSub: { fontSize: 16, color: 'var(--ink-3)', lineHeight: 1.55, margin: 0, maxWidth: 540 } as React.CSSProperties,
  body: { padding: '32px 48px 36px' } as React.CSSProperties,
  sectionLabel: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, fontWeight: 600, letterSpacing: '0.02em', textTransform: 'uppercase' as const, marginBottom: 12, color: 'var(--ink-2)' } as React.CSSProperties,
  dot: { width: 22, height: 22, borderRadius: '50%', background: 'var(--violet)', color: 'white', display: 'grid', placeItems: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500 } as React.CSSProperties,
  helper: { fontSize: 14, color: 'var(--ink-3)', marginBottom: 14, lineHeight: 1.55 } as React.CSSProperties,
  divider: { height: 1, background: 'var(--line-2)', margin: '32px 0' } as React.CSSProperties,
  footer: { padding: '20px 48px 28px', borderTop: '1px solid var(--line-2)', background: 'rgba(0,0,0,0.30)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' } as React.CSSProperties,
  note: { fontSize: 13, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 8 } as React.CSSProperties,
  submit: { display: 'inline-flex', alignItems: 'center', gap: 10, padding: '14px 22px', borderRadius: 999, background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))', color: 'white', fontSize: 15, fontWeight: 500, boxShadow: '0 6px 20px -6px rgba(168,85,247,0.6)', cursor: 'pointer', border: 'none' } as React.CSSProperties,
  submitOff: { opacity: 0.35, cursor: 'not-allowed', boxShadow: 'none' } as React.CSSProperties,
}

export function OnboardForm() {
  const navigate = useNavigate()
  const [form, setForm]             = useState<FormState>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState<string | null>(null)

  const canSubmit = !!form.payslipResult && FUNDA_LISTING_REGEX.test(form.fundaUrl ?? '')

  async function handleSubmit() {
    if (!canSubmit || !form.payslipResult) return
    setSubmitting(true)
    setError(null)
    try {
      const p = form.payslipResult
      const res = await submitOnboard({
        payslip: {
          gross_monthly_eur: p.payslip.gross_monthly_eur ?? 0,
          net_monthly_eur:   p.payslip.net_monthly_eur ?? 0,
          employer_name:     p.payslip.employer_name,
          pay_period:        p.payslip.pay_period,
          confidence:        p.confidence,
        },
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
    <div style={us.page}>
      {/* Top bar */}
      <div style={us.topbar}>
        <button onClick={() => navigate('/')} style={us.back}>
          <Icon name="arrow-left" size={16}/> Back
        </button>
        <div style={us.brand}>
          <div style={us.brandMark}>n</div>
          <span>bunq <span style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--violet-2)' }}>Nest</span></span>
        </div>
        <div style={{ width: 60 }}/>
      </div>

      {/* Card */}
      <div style={us.card} className="animate-fade-up">
        {/* Header */}
        <div style={us.header}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: 'var(--rainbow)', opacity: 0.85 }}/>
          <h1 style={us.greet}>Hi <span style={{ fontStyle: 'italic', color: 'var(--violet-2)' }}>Tim</span></h1>
          <p style={us.greetSub}>Two quick things and your coach can take it from here. We'll keep everything private — promise.</p>
        </div>

        {/* Body */}
        <div style={us.body}>
          {/* Step 1 — Payslip */}
          <div style={us.sectionLabel}><span style={us.dot}>1</span>Your latest payslip</div>
          <p style={us.helper}>Upload, snap a photo, or drag it in. PDFs and JPGs both work — we'll read the income for you.</p>
          <PayslipUpload onComplete={(payslipResult) => setForm((f) => ({ ...f, payslipResult }))} />

          <div style={us.divider}/>

          {/* Step 2 — Funda */}
          <div style={us.sectionLabel}><span style={us.dot}>2</span>The home you have your eye on</div>
          <p style={us.helper}>Drop a Funda link here. Just browsing? You can always come back with one later.</p>
          <FundaInput
            value={form.fundaUrl ?? ''}
            onChange={(fundaUrl, fundaPriceOverride) =>
              setForm((f) => ({ ...f, fundaUrl, fundaPriceOverride }))
            }
          />
        </div>

        {/* Footer */}
        <div style={us.footer}>
          <div style={us.note}>
            <Icon name="shield" size={14} color="var(--violet-2)"/>
            Encrypted and stored in the EU. Never shared.
          </div>
          <button
            disabled={!canSubmit || submitting}
            onClick={handleSubmit}
            style={{ ...us.submit, ...(canSubmit && !submitting ? {} : us.submitOff) }}
          >
            {submitting ? 'Preparing your plan...' : 'Meet your coach'}
            {!submitting && <Icon name="arrow-right" size={16}/>}
          </button>
        </div>
      </div>

      {/* Progress indicator */}
      <div style={{ maxWidth: 880, margin: '20px auto 0', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontSize: 13, color: 'var(--ink-3)' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <div style={{ width: 28, height: 4, borderRadius: 2, background: 'var(--violet)' }}/>
          <div style={{ width: 28, height: 4, borderRadius: 2, background: canSubmit ? 'var(--violet)' : 'var(--line)' }}/>
          <div style={{ width: 28, height: 4, borderRadius: 2, background: 'var(--line)' }}/>
        </div>
        <span>Step 2 of 3</span>
      </div>

      {error && <div style={{ maxWidth: 880, margin: '12px auto 0', fontSize: 13, color: 'var(--terracotta)', textAlign: 'center' }}>{error}</div>}
    </div>
  )
}
