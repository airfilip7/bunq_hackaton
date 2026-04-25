import type { ToolCallRecord } from '@/api/types'

const TOOL_LABELS: Record<string, string> = {
  get_bunq_transactions: 'checking transactions',
  get_bunq_buckets:      'checking buckets',
  get_funda_property:    'fetching property',
  compute_projection:    'computing projection',
}

type Props = { toolCall: ToolCallRecord }

export function ToolPill({ toolCall }: Props) {
  const label    = TOOL_LABELS[toolCall.name] ?? toolCall.name
  const resolved = toolCall.result !== undefined

  if (!resolved) {
    return (
      <span className="pill pill-live">
        <span className="pill-dot" />
        {label}
      </span>
    )
  }

  return (
    <span className="pill">
      <span className="pill-check">
        <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
          <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      {label}
    </span>
  )
}
