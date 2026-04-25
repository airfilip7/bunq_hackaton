import { useState } from 'react'
import { Input } from '@/components/ui/input'

const FUNDA_REGEX = /^https:\/\/(www\.)?funda\.nl\//

type Props = {
  value: string
  onChange: (url: string, priceOverride?: number) => void
}

export function FundaInput({ value, onChange }: Props) {
  const [showManual, setShowManual] = useState(false)
  const [manualPrice, setManualPrice] = useState('')

  const isValid = FUNDA_REGEX.test(value)

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-text-secondary">Funda listing URL</label>
      <Input
        type="url"
        placeholder="https://www.funda.nl/koop/..."
        value={value}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value, manualPrice ? Number(manualPrice) : undefined)}
        className="bg-surface-2 border-surface-3 text-text-primary placeholder:text-text-disabled"
      />
      {value && !isValid && (
        <p className="text-error text-xs">Paste a funda.nl listing URL</p>
      )}
      {isValid && (
        <button
          type="button"
          className="text-xs text-text-secondary underline text-left"
          onClick={() => setShowManual((v) => !v)}
        >
          Price not parsed correctly? Enter manually
        </button>
      )}
      {showManual && (
        <Input
          type="number"
          placeholder="Price in € (e.g. 425000)"
          value={manualPrice}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
            setManualPrice(e.target.value)
            onChange(value, Number(e.target.value))
          }}
          className="bg-surface-2 border-surface-3 text-text-primary"
        />
      )}
    </div>
  )
}
