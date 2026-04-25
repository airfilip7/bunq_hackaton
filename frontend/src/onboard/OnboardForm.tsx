import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { PayslipUpload } from './PayslipUpload'
import { FundaInput } from './FundaInput'
import { submitOnboard } from '@/api/onboard'

type FormState = {
  s3Key?: string
  fundaUrl?: string
  fundaPriceOverride?: number
}

export function OnboardForm() {
  const navigate = useNavigate()
  const [form, setForm]     = useState<FormState>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]   = useState<string | null>(null)

  const canSubmit = !!form.s3Key && !!form.fundaUrl

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
      navigate(`/chat?bootstrap=${res.session_id}`)
    } catch {
      setError('Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto mt-16 flex flex-col gap-8 px-4">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">
          Get your home-buying picture
        </h1>
        <p className="text-text-secondary text-sm mt-1">
          Two steps — takes about 60 seconds.
        </p>
      </div>

      {/* Step 1 — Payslip */}
      <section className="flex flex-col gap-3">
        <StepLabel n={1} label="Your latest payslip" done={!!form.s3Key} />
        <PayslipUpload onComplete={(s3Key) => setForm((f) => ({ ...f, s3Key }))} />
      </section>

      {/* Step 2 — Funda */}
      {form.s3Key && (
        <section className="flex flex-col gap-3">
          <StepLabel n={2} label="The property you have in mind" done={!!form.fundaUrl} />
          <FundaInput
            value={form.fundaUrl ?? ''}
            onChange={(fundaUrl, fundaPriceOverride) =>
              setForm((f) => ({ ...f, fundaUrl, fundaPriceOverride }))
            }
          />
        </section>
      )}

      {/* Submit */}
      {canSubmit && (
        <Button
          className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90"
          disabled={submitting}
          onClick={handleSubmit}
        >
          {submitting ? 'Preparing your picture…' : 'See my home-buying picture'}
        </Button>
      )}
      {error && <p className="text-error text-sm">{error}</p>}
    </div>
  )
}

function StepLabel({ n, label, done }: { n: number; label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={[
          'w-6 h-6 rounded-full text-xs flex items-center justify-center font-medium',
          done ? 'bg-bunq-teal text-surface-0' : 'bg-surface-2 text-text-secondary',
        ].join(' ')}
      >
        {done ? '✓' : n}
      </span>
      <span className="text-sm font-medium text-text-primary">{label}</span>
    </div>
  )
}
