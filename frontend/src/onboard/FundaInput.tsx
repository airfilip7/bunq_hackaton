import { useState, useEffect } from 'react'
import { Icon } from '@/components/Icon'
import { parseFunda } from '@/api/onboard'
import type { FundaParseResult } from '@/api/types'

const FUNDA_LISTING_REGEX = /^https:\/\/(www\.)?funda\.nl\/(detail\/)?(koop|huur|nieuwbouw)\//
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

function priceError(raw: string): string | null {
  if (!raw) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0) return 'Enter a valid price.'
  if (n < MIN_PRICE) return `Price seems too low (min \u20AC${MIN_PRICE.toLocaleString('nl-NL')}).`
  if (n > MAX_PRICE) return `Price seems too high (max \u20AC${MAX_PRICE.toLocaleString('nl-NL')}).`
  return null
}

type ParseState = 'idle' | 'loading' | 'done' | 'error'

type Props = {
  value: string
  onChange: (url: string, priceOverride?: number) => void
}

export function FundaInput({ value, onChange }: Props) {
  const [focus, setFocus] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [manualPrice, setManualPrice] = useState('')
  const [parseState, setParseState] = useState<ParseState>('idle')
  const [parseResult, setParseResult] = useState<FundaParseResult | null>(null)

  const priceErr = priceError(manualPrice)
  const isValid  = FUNDA_LISTING_REGEX.test(value)

  useEffect(() => {
    if (!isValid) {
      setParseState('idle')
      setParseResult(null)
      return
    }

    let cancelled = false
    setParseState('loading')
    setParseResult(null)

    parseFunda(value)
      .then((result) => {
        if (cancelled) return
        setParseResult(result)
        setParseState('done')
        if (result.price_eur) {
          onChange(value, result.price_eur)
        }
      })
      .catch(() => {
        if (cancelled) return
        setParseState('error')
      })

    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, isValid])

  function handleUrlChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(sanitizeUrl(e.target.value), manualPrice ? Number(manualPrice) : undefined)
  }

  function handlePriceChange(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value
    setManualPrice(raw)
    if (!priceError(raw) && raw) onChange(value, Number(raw))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* URL input */}
      <div style={{
        background: 'rgba(255,255,255,0.04)', border: `1.5px solid ${focus ? 'var(--violet)' : 'var(--line)'}`,
        borderRadius: 16, padding: '4px 4px 4px 18px',
        display: 'flex', alignItems: 'center', gap: 12,
        transition: 'border-color 0.15s, box-shadow 0.15s',
        boxShadow: focus ? '0 0 0 4px var(--violet-soft)' : 'none',
      }}>
        <Icon name="link" size={18} color="var(--ink-3)"/>
        <input
          type="url"
          placeholder="https://www.funda.nl/koop/amsterdam/huis-..."
          value={value}
          onChange={handleUrlChange}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          style={{
            flex: 1, border: 'none', outline: 'none', fontSize: 15,
            padding: '16px 0', color: 'white', background: 'transparent', minWidth: 0,
            fontFamily: 'inherit',
          }}
        />
        {isValid && (
          <div style={{
            background: 'var(--violet-soft)', color: 'var(--violet-2)',
            padding: '6px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600,
            display: 'inline-flex', alignItems: 'center', gap: 4,
            border: '1px solid rgba(168,85,247,0.3)',
          }}>
            <Icon name="check" size={12}/> Found it
          </div>
        )}
      </div>

      {/* Property preview */}
      {isValid && parseState === 'done' && parseResult && (
        <div className="animate-fade-up" style={{
          display: 'flex', gap: 16, padding: 16,
          background: 'rgba(168,85,247,0.08)', borderRadius: 16,
          border: '1px solid var(--line)',
        }}>
          <div style={{
            width: 100, height: 80, borderRadius: 10, flexShrink: 0,
            overflow: 'hidden', border: '1px solid var(--line)',
          }}>
            <svg viewBox="0 0 100 80" width="100" height="80">
              <rect width="100" height="80" fill="#7C3AED"/>
              <path d="M0 60 L30 40 L50 50 L75 30 L100 45 L100 80 L0 80 Z" fill="#5B21B6"/>
              <rect x="40" y="38" width="20" height="22" fill="#1E0B36" stroke="#C084FC" strokeWidth="0.8"/>
              <path d="M40 38 L50 30 L60 38 Z" fill="#A855F7"/>
              <rect x="46" y="46" width="3" height="6" fill="#22D3EE"/>
              <rect x="52" y="46" width="3" height="6" fill="#22D3EE"/>
            </svg>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--ink-4)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <Icon name="pin" size={12}/>
              {parseResult.address ?? 'Listing found'}
            </div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22, lineHeight: 1.1, marginBottom: 6 }}>
              {parseResult.price_eur
                ? <>&euro; {parseResult.price_eur.toLocaleString('nl-NL')} <span style={{ fontSize: 13, color: 'var(--ink-3)', fontFamily: 'var(--font-sans)' }}>k.k.</span></>
                : 'Price not found'
              }
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-3)', display: 'flex', gap: 14 }}>
              {parseResult.size_m2 && <span>{parseResult.size_m2} m&sup2;</span>}
            </div>
          </div>
        </div>
      )}

      {isValid && parseState === 'loading' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--line)' }}>
          <Icon name="loader" size={16} color="var(--violet-2)"/>
          <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>Reading listing...</span>
        </div>
      )}

      {/* Manual price */}
      {isValid && (
        <button
          type="button"
          style={{ fontSize: 12, color: 'var(--ink-3)', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: 0 }}
          onClick={() => setShowManual((v) => !v)}
        >
          {parseState === 'error' || (parseState === 'done' && !parseResult?.price_eur)
            ? 'Enter price manually'
            : 'Price not correct? Enter manually'
          }
        </button>
      )}

      {showManual && (
        <>
          <input
            className="input-field"
            type="number"
            placeholder="Price in \u20AC (e.g. 425000)"
            value={manualPrice}
            min={MIN_PRICE}
            max={MAX_PRICE}
            onChange={handlePriceChange}
          />
          {priceErr && <div style={{ fontSize: 11.5, color: 'var(--terracotta)' }}>{priceErr}</div>}
        </>
      )}
    </div>
  )
}
