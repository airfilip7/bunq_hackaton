import { Button } from '@/components/ui/button'
import { useChatStore } from '@/chat/chatStore'

// Lights up when the agent reports months_to_goal <= 6.
// For now we drive this from the store; the agent turn can update it via a dedicated field.
type Props = { monthsToGoal: number | null }

export function HandoffCTA({ monthsToGoal }: Props) {
  const ready = monthsToGoal !== null && monthsToGoal <= 6

  return (
    <div className="fixed bottom-24 right-4">
      <Button
        disabled={!ready}
        title={ready ? 'Connect with a licensed advisor' : 'Available when you\'re within 6 months of your goal'}
        className={[
          'rounded-full shadow-lg text-sm px-4 py-2 transition-all',
          ready
            ? 'bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90'
            : 'bg-surface-2 text-text-disabled cursor-not-allowed opacity-40',
        ].join(' ')}
      >
        Talk to an advisor
      </Button>
    </div>
  )
}

// Re-export a wired version that reads directly from the store.
// Pass monthsToGoal={null} until the profile is loaded.
export function HandoffCTAConnected() {
  // TODO: wire to profile.projection.months_to_goal once profile is in store.
  void useChatStore  // silence unused import lint until wired
  return <HandoffCTA monthsToGoal={null} />
}
