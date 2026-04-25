import { useRef, useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { StreamState } from './chatStore'

type Props = {
  streamState: StreamState
  onSend: (text: string) => void
}

export function Composer({ streamState, onSend }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Composer is always enabled except mid-stream.
  // Sending while awaiting_approval = implicit deny + new message (handled in ChatView).
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
    <div className="flex gap-2 p-4 border-t border-surface-3 bg-surface-0">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? 'Waiting for response…' : 'Ask anything about your home-buying goal…'}
        className="bg-surface-2 border-surface-3 text-text-primary placeholder:text-text-disabled"
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90 shrink-0"
      >
        Send
      </Button>
    </div>
  )
}
