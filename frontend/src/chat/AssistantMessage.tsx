import { Icon } from '@/components/Icon'
import { Markdown } from '@/components/Markdown'
import { ToolPill } from './ToolPill'
import type { Message } from '@/api/types'

function AssistantAvatar() {
  return (
    <div style={{
      width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
      background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
      color: 'white', display: 'grid', placeItems: 'center',
      boxShadow: '0 0 0 3px var(--violet-soft)',
    }}>
      <Icon name="bunq" size={20} stroke={2}/>
    </div>
  )
}

type Props = { message: Message }

export function AssistantMessage({ message }: Props) {
  return (
    <div className="animate-fade-up" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
      <AssistantAvatar />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 560 }}>
        {(message.tool_calls ?? []).length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {message.tool_calls!.map((tc) => (
              <ToolPill key={tc.tool_use_id} toolCall={tc} />
            ))}
          </div>
        )}
        {message.content && (
          <div style={{
            padding: '14px 18px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 18, borderTopLeftRadius: 6,
            border: '1px solid var(--line)',
            fontSize: 15, lineHeight: 1.55, color: 'var(--ink)',
          }}>
            <Markdown text={message.content} />
            {message.streaming && <span className="bunq-cursor" />}
          </div>
        )}
      </div>
    </div>
  )
}
