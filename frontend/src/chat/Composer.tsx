import { useRef, useState } from 'react'
import { Icon } from '@/components/Icon'
import type { StreamState } from './chatStore'

const SUGGESTIONS = [
  'What if I bought together?',
  'Show me cheaper homes',
  'Save \u20AC500/mo plan',
]

type Props = {
  streamState: StreamState
  onSend: (text: string) => void
}

export function Composer({ streamState, onSend }: Props) {
  const [value, setValue] = useState('')
  const [focus, setFocus] = useState(false)
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
      padding: '16px 28px 24px',
      borderTop: '1px solid var(--line-2)',
      background: 'rgba(0,0,0,0.30)',
      backdropFilter: 'blur(12px)',
    }}>
      <div style={{
        maxWidth: 760, margin: '0 auto',
        background: 'rgba(255,255,255,0.05)',
        borderRadius: 22, border: `1.5px solid ${focus ? 'var(--violet)' : 'var(--line)'}`,
        padding: '10px 10px 10px 20px',
        display: 'flex', alignItems: 'center', gap: 10,
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
        boxShadow: focus ? '0 0 0 4px var(--violet-soft)' : 'none',
      }}>
        <Icon name="sparkles" size={18} color="var(--violet-2)"/>
        <input
          ref={inputRef}
          placeholder={disabled ? 'Waiting...' : "Ask anything \u2014 'what if I made \u20AC500 more?'"}
          value={value}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          style={{
            flex: 1, border: 'none', outline: 'none', fontSize: 15,
            padding: '12px 0', background: 'transparent', color: 'white',
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          style={{
            width: 40, height: 40, borderRadius: 999,
            background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
            color: 'white', display: 'grid', placeItems: 'center',
            opacity: value.trim() ? 1 : 0.4,
            cursor: value.trim() ? 'pointer' : 'default',
            border: 'none',
          }}
        >
          <Icon name="send" size={16}/>
        </button>
      </div>

      {/* Suggestion chips */}
      <div style={{ maxWidth: 760, margin: '12px auto 0', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setValue(s)}
            style={{
              fontSize: 13, color: 'var(--ink-2)',
              background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)',
              padding: '8px 14px', borderRadius: 999, cursor: 'pointer',
              transition: 'background 0.15s, border-color 0.15s, color 0.15s',
            }}
            onMouseEnter={(e) => { const t = e.currentTarget; t.style.background = 'var(--violet-soft)'; t.style.borderColor = 'rgba(168,85,247,0.4)'; t.style.color = 'var(--violet-2)' }}
            onMouseLeave={(e) => { const t = e.currentTarget; t.style.background = 'rgba(255,255,255,0.04)'; t.style.borderColor = 'var(--line)'; t.style.color = 'var(--ink-2)' }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
