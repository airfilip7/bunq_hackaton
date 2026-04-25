import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { PayslipUpload } from './PayslipUpload'
import { FundaInput } from './FundaInput'
import { BunqConnect } from './BunqConnect'
import { submitOnboard } from '@/api/onboard'

type Step = 'payslip' | 'funda' | 'bunq'

type FormState = {
  s3Key?: string
  fundaUrl?: string
  fundaPriceOverride?: number
  bunqOauthState?: string
}

// Persist form state across the bunq OAuth redirect.
const STORAGE_KEY = 'bunq_nest.onboard_state'

export function OnboardForm() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('payslip')
  const [form, setForm] = useState<FormState>(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? (JSON.parse(saved) as FormState) : {}
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function saveForm(update: Partial<FormState>) {
    const next = { ...form, ...update }
    setForm(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  async function handleSubmit() {
    if (!form.s3Key || !form.fundaUrl || !form.bunqOauthState) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await submitOnboard({
        s3_key:                    form.s3Key,
        funda_url:                 form.fundaUrl,
        funda_price_override_eur:  form.fundaPriceOverride,
        bunq_oauth_state:          form.bunqOauthState,
      })
      localStorage.removeItem(STORAGE_KEY)
      navigate(`/chat?bootstrap=${res.session_id}`)
    } catch {
      setError('Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto mt-16 flex flex-col gap-8 px-4">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Get your home-buying picture</h1>
        <p className="text-text-secondary text-sm mt-1">
          Three steps — takes about 90 seconds.
        </p>
      </div>

      {/* Step 1 — Payslip */}
      <section className="flex flex-col gap-3">
        <StepLabel n={1} label="Your latest payslip" done={!!form.s3Key} />
        {(!form.s3Key || step === 'payslip') && (
          <PayslipUpload
            onComplete={(s3Key) => {
              saveForm({ s3Key })
              setStep('funda')
            }}
          />
        )}
      </section>

      {/* Step 2 — Funda */}
      {(step === 'funda' || form.fundaUrl) && (
        <section className="flex flex-col gap-3">
          <StepLabel n={2} label="The property you have in mind" done={!!form.fundaUrl} />
          <FundaInput
            value={form.fundaUrl ?? ''}
            onChange={(fundaUrl, fundaPriceOverride) => saveForm({ fundaUrl, fundaPriceOverride })}
          />
          {form.fundaUrl && step === 'funda' && (
            <Button
              className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90"
              onClick={() => setStep('bunq')}
            >
              Continue
            </Button>
          )}
        </section>
      )}

      {/* Step 3 — bunq OAuth */}
      {step === 'bunq' && (
        <section className="flex flex-col gap-3">
          <StepLabel n={3} label="Connect bunq" done={!!form.bunqOauthState} />
          {!form.bunqOauthState ? (
            <BunqConnect />
          ) : (
            <>
              <p className="text-bunq-teal text-sm">✓ bunq connected</p>
              <Button
                className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90"
                disabled={submitting}
                onClick={handleSubmit}
              >
                {submitting ? 'Preparing your picture…' : 'See my home-buying picture'}
              </Button>
              {error && <p className="text-error text-sm">{error}</p>}
            </>
          )}
        </section>
      )}
    </div>
  )
}

function StepLabel({ n, label, done }: { n: number; label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={[
        'w-6 h-6 rounded-full text-xs flex items-center justify-center font-medium',
        done ? 'bg-bunq-teal text-surface-0' : 'bg-surface-2 text-text-secondary',
      ].join(' ')}>
        {done ? '✓' : n}
      </span>
      <span className="text-sm font-medium text-text-primary">{label}</span>
    </div>
  )
}
