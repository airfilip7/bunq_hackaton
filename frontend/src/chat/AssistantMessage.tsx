import { ToolPill } from './ToolPill'
import type { Message } from '@/api/types'

function AssistantAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 999, flexShrink: 0,
      background: 'linear-gradient(135deg, var(--bunq-teal), #0fa5a5)',
      color: '#06222a',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, fontWeight: 700,
    }}>
      b
    </div>
  )
}

type Props = { message: Message }

export function AssistantMessage({ message }: Props) {
  return (
    <div style={{ display: 'flex', gap: 10, padding: '0 16px', alignItems: 'flex-start' }}>
      <AssistantAvatar />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: '82%' }}>
        {(message.tool_calls ?? []).length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {message.tool_calls!.map((tc) => (
              <ToolPill key={tc.tool_use_id} toolCall={tc} />
            ))}
          </div>
        )}
        <div style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
          {message.content}
          {message.streaming && <span className="bunq-cursor" />}
        </div>
      </div>
    </div>
  )
}
