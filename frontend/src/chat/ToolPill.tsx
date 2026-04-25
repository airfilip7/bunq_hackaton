import type { ToolCallRecord } from '@/api/types'

const TOOL_LABELS: Record<string, string> = {
  get_bunq_transactions: 'checking transactions',
  get_bunq_buckets:      'checking buckets',
  get_funda_property:    'fetching property',
  compute_projection:    'computing projection',
}

type Props = { toolCall: ToolCallRecord }

export function ToolPill({ toolCall }: Props) {
  const label   = TOOL_LABELS[toolCall.name] ?? toolCall.name
  const resolved = toolCall.result !== undefined

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        resolved
          ? 'bg-surface-2 text-text-secondary'
          : 'bg-surface-2 text-bunq-teal animate-pulse',
      ].join(' ')}
    >
      {resolved ? '✓' : '·'} {label}
    </span>
  )
}
