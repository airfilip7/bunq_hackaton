import { ToolPill } from './ToolPill'
import type { Message } from '@/api/types'

type Props = { message: Message }

export function AssistantMessage({ message }: Props) {
  return (
    <div className="flex flex-col gap-2 max-w-2xl">
      {/* Tool pills — shown above the text */}
      {(message.tool_calls ?? []).length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.tool_calls!.map((tc) => (
            <ToolPill key={tc.tool_use_id} toolCall={tc} />
          ))}
        </div>
      )}

      {/* Message text */}
      <div className="text-text-primary text-sm leading-relaxed whitespace-pre-wrap">
        {message.content}
        {/* Blinking cursor while streaming */}
        {message.streaming && (
          <span className="inline-block w-0.5 h-4 bg-bunq-teal ml-0.5 animate-pulse align-middle" />
        )}
      </div>
    </div>
  )
}
