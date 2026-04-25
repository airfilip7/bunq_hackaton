import { useState } from 'react'
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
    <div style={{
      background: 'var(--surface-2)',
      borderRadius: 16,
      borderLeft: '3px solid var(--bunq-yellow)',
      padding: '16px 16px 14px 18px',
      display: 'flex', flexDirection: 'column', gap: 12,
      boxShadow: '0 8px 24px -12px rgba(0,0,0,0.4)',
    }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--bunq-yellow)', letterSpacing: '0.1em', fontWeight: 600, textTransform: 'uppercase' }}>
            Suggested action
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: 1.3 }}>
            {proposal.summary}
          </div>
        </div>
        <span className={`badge badge-${proposal.risk_level === 'low' ? 'low' : 'low'}`}>
          <span className="badge-dot" />
          {proposal.risk_level} risk
        </span>
      </div>

      {/* Money flow */}
      {isMoveMoney && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 12px',
          background: 'var(--surface-1)',
          border: '1px solid var(--surface-3)',
          borderRadius: 10,
        }}>
          {/* From */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(255,215,46,0.12)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--bunq-yellow)',
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
              </svg>
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.2 }}>From</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {params.from_bucket_name}
              </div>
            </div>
          </div>

          {/* Amount + arrow */}
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
              <div className="t-num" style={{ fontSize: 16, fontWeight: 700, color: 'var(--bunq-teal)', letterSpacing: '-0.01em' }}>
                €{params.amount_eur.toLocaleString('nl-NL')}
              </div>
            )}
            <svg width="40" height="6" viewBox="0 0 40 6" fill="none">
              <path d="M0 3 H34 M30 0 L34 3 L30 6" stroke="var(--bunq-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
          </div>

          {/* To */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0, justifyContent: 'flex-end' }}>
            <div style={{ minWidth: 0, textAlign: 'right' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.2 }}>To</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {params.to_bucket_name}
              </div>
            </div>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(30,200,200,0.12)',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--bunq-teal)',
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 11.5L12 4l9 7.5" /><path d="M5 10v9h14v-9" />
              </svg>
            </div>
          </div>
        </div>
      )}

      {/* Rationale */}
      <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text-secondary)' }}>
        {proposal.rationale}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
        <button
          className="btn btn-primary"
          onClick={handleApprove}
          disabled={disabled}
          style={{ flex: 1 }}
        >
          Approve
        </button>
        {isMoveMoney && !editing && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setEditing(true)}
            disabled={disabled}
            style={{ height: 40, borderRadius: 10 }}
          >
            Edit amount
          </button>
        )}
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => onDeny()}
          disabled={disabled}
          style={{ height: 40, borderRadius: 10 }}
        >
          Not now
        </button>
      </div>
    </div>
  )
}
