import { Icon } from '@/components/Icon'
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
        <Icon name="check" size={9}/>
      </span>
      {label}
    </span>
  )
}
