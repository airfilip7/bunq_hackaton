import { useState } from 'react'
import { Icon } from '@/components/Icon'
import type { ToolProposal, ProposeMoveMoneyParams } from '@/api/types'

type Props = {
  proposal: ToolProposal
  disabled?: boolean
  onApprove: (overrides?: { amount_eur?: number }) => void
  onDeny:    (feedback?: string) => void
}

export function ApprovalCard({ proposal, disabled, onApprove, onDeny }: Props) {
  const [editing, setEditing]       = useState(false)
  const [editAmount, setEditAmount] = useState('')

  const isMoveMoney = proposal.name === 'propose_move_money'
  const params      = proposal.params as ProposeMoveMoneyParams

  function handleApprove() {
    onApprove(editing && editAmount ? { amount_eur: parseFloat(editAmount) } : undefined)
  }

  return (
    <div className="animate-fade-up" style={{
      background: 'rgba(255,255,255,0.04)',
      borderRadius: 18,
      borderLeft: '3px solid var(--violet-2)',
      padding: '18px 18px 16px 20px',
      display: 'flex', flexDirection: 'column', gap: 14,
      border: '1px solid var(--line)',
      boxShadow: 'var(--shadow)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--violet-2)', letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase' }}>
            Suggested action
          </div>
          <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--ink)', letterSpacing: '-0.01em', lineHeight: 1.3 }}>
            {proposal.summary}
          </div>
        </div>
        <span className="badge badge-low">
          <span className="badge-dot" />
          {proposal.risk_level} risk
        </span>
      </div>

      {/* Money flow */}
      {isMoveMoney && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 14px',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--line)',
          borderRadius: 14,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(168,85,247,0.12)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--violet-2)',
            }}>
              <Icon name="wallet" size={14}/>
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', lineHeight: 1.2 }}>From</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {params.from_bucket_name}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, padding: '0 4px' }}>
            {editing ? (
              <input
                className="input-field"
                type="number"
                style={{ width: 80, height: 32, borderRadius: 8, fontSize: 13, textAlign: 'center', padding: '0 8px' }}
                placeholder={String(params.amount_eur)}
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                autoFocus
              />
            ) : (
              <div className="t-num" style={{ fontSize: 16, fontWeight: 700, color: 'var(--violet-2)', letterSpacing: '-0.01em' }}>
                &euro;{params.amount_eur.toLocaleString('nl-NL')}
              </div>
            )}
            <svg width="40" height="6" viewBox="0 0 40 6" fill="none">
              <path d="M0 3 H34 M30 0 L34 3 L30 6" stroke="var(--violet-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0, justifyContent: 'flex-end' }}>
            <div style={{ minWidth: 0, textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', lineHeight: 1.2 }}>To</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {params.to_bucket_name}
              </div>
            </div>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'var(--violet-soft)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--violet-2)',
            }}>
              <Icon name="house" size={14}/>
            </div>
          </div>
        </div>
      )}

      {/* Rationale */}
      <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--ink-3)' }}>
        {proposal.rationale}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
        <button className="btn btn-primary" onClick={handleApprove} disabled={disabled} style={{ flex: 1 }}>
          Approve
        </button>
        {isMoveMoney && !editing && (
          <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)} disabled={disabled} style={{ height: 40, borderRadius: 999 }}>
            Edit amount
          </button>
        )}
        <button className="btn btn-ghost btn-sm" onClick={() => onDeny()} disabled={disabled} style={{ height: 40, borderRadius: 999 }}>
          Not now
        </button>
      </div>
    </div>
  )
}
