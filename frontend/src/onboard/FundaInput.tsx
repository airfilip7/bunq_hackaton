import { useState } from 'react'

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
  } catch { return trimmed }
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
    onChange(sanitizeUrl(e.target.value), manualPrice ? Number(manualPrice) : undefined)
  }

  function handlePriceChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    setManualPrice(raw)
    if (!priceError(raw) && raw) onChange(value, Number(raw))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* URL input with link icon */}
      <div style={{ position: 'relative' }}>
        <div style={{
          position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--text-disabled)', pointerEvents: 'none',
          display: 'flex', alignItems: 'center',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
        </div>
        <input
          className="input-field"
          type="url"
          placeholder="https://www.funda.nl/koop/amsterdam/…"
          value={value}
          onChange={handleUrlChange}
          style={{ paddingLeft: 36, paddingRight: isValid ? 36 : 14 }}
        />
        {isValid && (
          <div style={{
            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
            width: 20, height: 20, borderRadius: 999,
            background: 'rgba(61,220,151,0.16)', color: 'var(--success)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 5L4 7L8 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        )}
      </div>

      {urlErr && <div style={{ fontSize: 11.5, color: 'var(--error)' }}>{urlErr}</div>}

      {/* Property preview card */}
      {isValid && (
        <div style={{
          padding: '10px 12px',
          background: 'var(--surface-2)', border: '1px solid var(--surface-3)',
          borderRadius: 10,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8, flexShrink: 0,
            background: 'linear-gradient(135deg, var(--surface-4), var(--surface-2))',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-secondary)',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 11.5L12 4l9 7.5" /><path d="M5 10v9h14v-9" /><path d="M10 19v-5h4v5" />
            </svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Listing detected
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 2 }}>
              Price will be extracted on submit
            </div>
          </div>
        </div>
      )}

      {isValid && (
        <button
          type="button"
          style={{ fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: 0 }}
          onClick={() => setShowManual((v) => !v)}
        >
          Price not parsed correctly? Enter manually
        </button>
      )}

      {showManual && (
        <>
          <input
            className="input-field"
            type="number"
            placeholder="Price in € (e.g. 425000)"
            value={manualPrice}
            min={MIN_PRICE}
            max={MAX_PRICE}
            onChange={handlePriceChange}
          />
          {priceErr && <div style={{ fontSize: 11.5, color: 'var(--error)' }}>{priceErr}</div>}
        </>
      )}

      <div style={{ fontSize: 11.5, color: 'var(--text-disabled)', lineHeight: 1.45 }}>
        Paste any Funda listing — we'll use it as your target to size the deposit.
      </div>
    </div>
  )
}
