import { useState } from 'react'
import { Input } from '@/components/ui/input'

// Must be a property listing path, not just funda.nl homepage.
const FUNDA_LISTING_REGEX = /^https:\/\/(www\.)?funda\.nl\/(koop|huur|nieuwbouw)\//

const TRACKING_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
const MIN_PRICE = 50_000
const MAX_PRICE = 5_000_000

function sanitizeUrl(raw: string): string {
  const trimmed = raw.trim()
  try {
    const url = new URL(trimmed)
    TRACKING_PARAMS.forEach((p) => url.searchParams.delete(p))
    return url.toString()
  } catch {
    return trimmed
  }
}

function urlError(url: string): string | null {
  if (!url) return null
  if (!FUNDA_LISTING_REGEX.test(url))
    return 'Paste a funda.nl listing URL — it should start with funda.nl/koop/ or funda.nl/huur/'
  return null
}

function priceError(raw: string): string | null {
  if (!raw) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return 'Enter a valid price.'
  if (n < MIN_PRICE) return `Price seems too low (min €${MIN_PRICE.toLocaleString('nl-NL')}).`
  if (n > MAX_PRICE) return `Price seems too high (max €${MAX_PRICE.toLocaleString('nl-NL')}).`
  return null
}

type Props = {
  value: string
  onChange: (url: string, priceOverride?: number) => void
}

export function FundaInput({ value, onChange }: Props) {
  const [showManual, setShowManual] = useState(false)
  const [manualPrice, setManualPrice] = useState('')

  const urlErr   = urlError(value)
  const priceErr = priceError(manualPrice)
  const isValid  = FUNDA_LISTING_REGEX.test(value)

  function handleUrlChange(e: React.ChangeEvent<HTMLInputElement>) {
    const sanitized = sanitizeUrl(e.target.value)
    onChange(sanitized, manualPrice ? Number(manualPrice) : undefined)
  }

  function handlePriceChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    setManualPrice(raw)
    // Only propagate if the value is valid — don't send garbage upstream.
    if (!priceError(raw) && raw) onChange(value, Number(raw))
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-text-secondary">Funda listing URL</label>
      <Input
        type="url"
        placeholder="https://www.funda.nl/koop/..."
        value={value}
        onChange={handleUrlChange}
        className="bg-surface-2 border-surface-3 text-text-primary placeholder:text-text-disabled"
      />
      {urlErr && <p className="text-error text-xs">{urlErr}</p>}

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
        <>
          <Input
            type="number"
            placeholder="Price in € (e.g. 425000)"
            value={manualPrice}
            min={MIN_PRICE}
            max={MAX_PRICE}
            onChange={handlePriceChange}
            className="bg-surface-2 border-surface-3 text-text-primary"
          />
          {priceErr && <p className="text-error text-xs">{priceErr}</p>}
        </>
      )}
    </div>
  )
}
