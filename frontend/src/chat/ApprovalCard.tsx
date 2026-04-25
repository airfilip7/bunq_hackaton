import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import type { ToolProposal, ProposeMoveMoneyParams } from '@/api/types'

const RISK_COLOURS = {
  low:    'bg-surface-2 text-text-secondary',
  medium: 'bg-bunq-yellow/20 text-bunq-yellow',
  high:   'bg-error/20 text-error',
}

type Props = {
  proposal: ToolProposal
  disabled?: boolean
  onApprove: (overrides?: { amount_eur?: number }) => void
  onDeny:    (feedback?: string) => void
}

export function ApprovalCard({ proposal, disabled, onApprove, onDeny }: Props) {
  const [editing, setEditing]     = useState(false)
  const [editAmount, setEditAmount] = useState('')

  const isMoveMoney = proposal.name === 'propose_move_money'
  const params      = proposal.params as ProposeMoveMoneyParams

  function handleApprove() {
    if (editing && editAmount) {
      onApprove({ amount_eur: parseFloat(editAmount) })
    } else {
      onApprove()
    }
  }

  return (
    <Card className="border-bunq-yellow/60 bg-surface-1 max-w-lg">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-medium text-text-primary">
            Suggested action — needs your approval
          </CardTitle>
          <Badge className={RISK_COLOURS[proposal.risk_level]}>
            {proposal.risk_level}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-4">
        {/* Summary */}
        <p className="text-base font-semibold text-text-primary">{proposal.summary}</p>

        {/* Move money detail */}
        {isMoveMoney && (
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <span>{params.from_bucket_name}</span>
            <span>→</span>
            <span>{params.to_bucket_name}</span>
            {editing ? (
              <Input
                type="number"
                className="w-24 h-7 text-sm"
                placeholder={String(params.amount_eur)}
                value={editAmount}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditAmount(e.target.value)}
                autoFocus
              />
            ) : (
              <span className="font-medium text-text-primary">€{params.amount_eur}</span>
            )}
          </div>
        )}

        {/* Rationale */}
        <p className="text-xs text-text-secondary">{proposal.rationale}</p>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={disabled}
            className="bg-bunq-teal text-surface-0 hover:bg-bunq-teal/90"
            onClick={handleApprove}
          >
            Approve
          </Button>

          {isMoveMoney && !editing && (
            <Button
              size="sm"
              variant="ghost"
              disabled={disabled}
              className="text-text-secondary"
              onClick={() => setEditing(true)}
            >
              Edit amount
            </Button>
          )}

          <Button
            size="sm"
            variant="ghost"
            disabled={disabled}
            className="text-text-secondary"
            onClick={() => onDeny()}
          >
            Not now
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}


