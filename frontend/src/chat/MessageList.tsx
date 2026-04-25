import { useEffect, useRef } from 'react'
import { AssistantMessage } from './AssistantMessage'
import { UserMessage } from './UserMessage'
import type { Message } from '@/api/types'

type Props = { messages: Message[] }

export function MessageList({ messages }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages])

  return (
    <div ref={scrollRef} style={{
      overflowY: 'auto', padding: '32px 28px 24px', minHeight: 0,
    }}>
      <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 22 }}>
        {messages.map((msg) =>
          msg.role === 'user'
            ? <UserMessage key={msg.id} content={msg.content} />
            : <AssistantMessage key={msg.id} message={msg} />,
        )}
      </div>
    </div>
  )
}
