import { useRef, useState } from 'react'
import type { StreamState } from './chatStore'

type Props = {
  streamState: StreamState
  onSend: (text: string) => void
}

export function Composer({ streamState, onSend }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const disabled = streamState === 'streaming'

  function handleSend() {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{
      padding: '10px 12px 14px',
      borderTop: '1px solid var(--surface-3)',
      background: 'var(--surface-0)',
      display: 'flex', gap: 8, alignItems: 'center',
      flexShrink: 0,
    }}>
      {/* Attach placeholder — wired up in a future iteration */}
      <button
        className="btn btn-ghost btn-sm"
        style={{ width: 40, height: 40, padding: 0, borderRadius: 12, flexShrink: 0 }}
        aria-label="attach"
        tabIndex={-1}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>

      <input
        ref={inputRef}
        className="input-field"
        style={{ height: 40, borderRadius: 12, fontSize: 13.5, flex: 1 }}
        placeholder={disabled ? 'Waiting…' : 'Ask anything about your home-buying goal…'}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />

      <button
        className="btn btn-primary"
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        style={{ height: 40, width: 40, padding: 0, borderRadius: 12, flexShrink: 0 }}
        aria-label="send"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12L19 5L12 19L10 13L5 12Z" />
        </svg>
      </button>
    </div>
  )
}
