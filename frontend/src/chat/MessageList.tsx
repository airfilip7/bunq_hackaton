import { useEffect, useRef } from 'react'
import { AssistantMessage } from './AssistantMessage'
import { UserMessage } from './UserMessage'
import type { Message } from '@/api/types'

function DayDivider({ label }: { label: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '4px 16px',
      color: 'var(--text-disabled)',
      fontSize: 11, fontWeight: 500, letterSpacing: '0.04em',
    }}>
      <div style={{ flex: 1, height: 1, background: 'var(--surface-3)' }} />
      <span>{label}</span>
      <div style={{ flex: 1, height: 1, background: 'var(--surface-3)' }} />
    </div>
  )
}

type Props = { messages: Message[] }

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 8, paddingBottom: 12 }}>
      {messages.length > 0 && <DayDivider label="Today" />}
      {messages.map((msg) =>
        msg.role === 'user'
          ? <UserMessage key={msg.id} content={msg.content} />
          : <AssistantMessage key={msg.id} message={msg} />,
      )}
      <div ref={bottomRef} />
    </div>
  )
}
