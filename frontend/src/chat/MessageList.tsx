import { useEffect, useRef } from 'react'
import { AssistantMessage } from './AssistantMessage'
import { UserMessage } from './UserMessage'
import type { Message } from '@/api/types'

type Props = { messages: Message[] }

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 flex flex-col gap-6">
      {messages.map((msg) =>
        msg.role === 'user' ? (
          <UserMessage key={msg.id} content={msg.content} />
        ) : (
          <AssistantMessage key={msg.id} message={msg} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  )
}
