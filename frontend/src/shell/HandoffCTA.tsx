import { Icon } from '@/components/Icon'
import { useChatStore } from '@/chat/chatStore'

type Props = { monthsToGoal: number | null }

export function HandoffCTA({ monthsToGoal }: Props) {
  const ready = monthsToGoal !== null && monthsToGoal <= 6

  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24 }}>
      <button
        disabled={!ready}
        title={ready ? 'Connect with a licensed advisor' : 'Available when you\'re within 6 months of your goal'}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '12px 20px', borderRadius: 999,
          fontSize: 14, fontWeight: 500,
          border: 'none', cursor: ready ? 'pointer' : 'not-allowed',
          boxShadow: ready ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
          transition: 'all 0.2s ease',
          ...(ready
            ? { background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))', color: 'white' }
            : { background: 'var(--surface)', color: 'var(--ink-4)', opacity: 0.5 }
          ),
        }}
      >
        <Icon name="chat" size={16}/>
        Talk to an advisor
      </button>
    </div>
  )
}

export function HandoffCTAConnected() {
  const monthsToGoal = useChatStore((s) => s.profile?.projection.months_to_goal ?? null)
  return <HandoffCTA monthsToGoal={monthsToGoal} />
}
