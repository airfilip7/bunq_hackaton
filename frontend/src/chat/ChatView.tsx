import { useEffect, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Icon } from '@/components/Icon'
import { MessageList } from './MessageList'
import { ApprovalCard } from './ApprovalCard'
import { Composer } from './Composer'
import { useChatStore } from './chatStore'
import { useChatStream } from './useChatStream'
import { HandoffCTAConnected } from '@/shell/HandoffCTA'
import { getSessions, getSession } from '@/api/chat'
import type { TurnRequest } from '@/api/types'

function newIk() { return crypto.randomUUID() }

/* ─── Styles ───────────────────────────────────────────────────────────── */

const cs = {
  page: { minHeight: '100vh', height: '100vh', display: 'grid', gridTemplateColumns: '320px 1fr', color: 'var(--ink)' } as React.CSSProperties,
  sidebar: {
    background: 'rgba(0,0,0,0.40)', borderRight: '1px solid var(--line-2)',
    padding: '20px 18px', display: 'flex', flexDirection: 'column' as const, gap: 18,
    overflowY: 'auto' as const, backdropFilter: 'blur(20px)',
  } as React.CSSProperties,
  brand: { display: 'flex', alignItems: 'center', gap: 10, fontWeight: 600, fontSize: 15, padding: '4px 6px' } as React.CSSProperties,
  brandMark: { width: 26, height: 26, borderRadius: 8, background: 'var(--rainbow)', color: 'white', display: 'grid', placeItems: 'center', fontFamily: 'var(--font-serif)', fontStyle: 'italic' as const, fontSize: 16 } as React.CSSProperties,
  sectionTitle: { fontSize: 11, fontWeight: 600, color: 'var(--ink-4)', letterSpacing: '0.08em', textTransform: 'uppercase' as const, padding: '0 6px', marginBottom: 8 } as React.CSSProperties,
  homeCard: { background: 'rgba(255,255,255,0.04)', borderRadius: 16, border: '1px solid var(--line)', padding: 14 } as React.CSSProperties,
  yourMath: { background: 'var(--violet-soft)', borderRadius: 16, padding: 14, border: '1px solid rgba(168,85,247,0.20)' } as React.CSSProperties,
  mathRow: { display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 13 } as React.CSSProperties,
  main: { display: 'grid', gridTemplateRows: 'auto 1fr auto', minHeight: 0 } as React.CSSProperties,
  topbar: {
    padding: '14px 28px', borderBottom: '1px solid var(--line-2)',
    background: 'rgba(11,6,18,0.7)', backdropFilter: 'blur(10px)',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  } as React.CSSProperties,
  coachBadge: { display: 'flex', alignItems: 'center', gap: 12 } as React.CSSProperties,
  coachAvatar: {
    width: 38, height: 38, borderRadius: '50%',
    background: 'linear-gradient(135deg, var(--violet), var(--violet-deep))',
    color: 'white', display: 'grid', placeItems: 'center',
    boxShadow: '0 0 0 3px var(--violet-soft)',
  } as React.CSSProperties,
}

/* ─── Chat Sidebar ─────────────────────────────────────────────────────── */

function ChatSidebar() {
  const profile = useChatStore((s) => s.profile)

  return (
    <aside style={cs.sidebar}>
      <div style={cs.brand}>
        <div style={cs.brandMark}>n</div>
        <span>bunq <span style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--violet-2)' }}>Nest</span></span>
      </div>

      {/* The home */}
      <div>
        <div style={cs.sectionTitle}>The home</div>
        <div style={cs.homeCard}>
          <svg viewBox="0 0 280 100" width="100%" style={{ borderRadius: 8, marginBottom: 10, display: 'block' }}>
            <rect width="280" height="100" fill="#5B21B6"/>
            <path d="M0 70 L60 50 L120 60 L180 35 L240 50 L280 45 L280 100 L0 100 Z" fill="#3B0F70"/>
            <rect x="120" y="48" width="40" height="42" fill="#1E0B36" stroke="#C084FC"/>
            <path d="M120 48 L140 32 L160 48 Z" fill="#A855F7"/>
            <rect x="130" y="60" width="6" height="14" fill="#22D3EE"/>
            <rect x="146" y="60" width="6" height="14" fill="#22D3EE"/>
            <circle cx="40" cy="20" r="2" fill="#C084FC"/>
            <circle cx="240" cy="15" r="1.5" fill="#22D3EE"/>
          </svg>
          <div style={{ fontSize: 11, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
            <Icon name="pin" size={10}/>
            {profile?.target.address ?? 'Your target home'}
          </div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 20, lineHeight: 1.1 }}>
            {profile ? `\u20AC ${profile.target.price_eur.toLocaleString('nl-NL')}` : '\u20AC ---'}
          </div>
          {/* size not in ProfileSnapshot — omit */}
        </div>
      </div>

      {/* Your numbers */}
      {profile && (
        <div>
          <div style={cs.sectionTitle}>Your numbers</div>
          <div style={cs.yourMath}>
            <div style={cs.mathRow}>
              <span style={{ color: 'var(--ink-3)' }}>Monthly gross</span>
              <span style={{ fontWeight: 500, fontFamily: 'var(--font-mono)', color: 'white' }}>
                &euro;{profile.payslip.gross_monthly_eur.toLocaleString('nl-NL')}
              </span>
            </div>
            <div style={cs.mathRow}>
              <span style={{ color: 'var(--ink-3)' }}>Net (avg)</span>
              <span style={{ fontWeight: 500, fontFamily: 'var(--font-mono)', color: 'white' }}>
                &euro;{profile.payslip.net_monthly_eur.toLocaleString('nl-NL')}
              </span>
            </div>
            <div style={cs.mathRow}>
              <span style={{ color: 'var(--ink-3)' }}>Savings (bunq)</span>
              <span style={{ fontWeight: 500, fontFamily: 'var(--font-mono)', color: 'white' }}>
                &euro;{profile.projection.savings_now_eur.toLocaleString('nl-NL')}
              </span>
            </div>
            <div style={{ height: 1, background: 'rgba(168,85,247,0.20)', margin: '8px 0' }}/>
            <div style={cs.mathRow}>
              <span style={{ color: 'var(--violet-2)', fontWeight: 500 }}>Borrowing power</span>
              <span style={{ fontWeight: 500, fontFamily: 'var(--font-mono)', color: 'var(--violet-2)' }}>
                &euro;{profile.projection.headroom_range_eur[0].toLocaleString('nl-NL')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div style={{ marginTop: 'auto', fontSize: 11, color: 'var(--ink-4)', lineHeight: 1.5, padding: '0 6px' }}>
        bunq Nest helps you prepare for homeownership. It is not mortgage advice.
        When you're ready to apply, bunq connects you with licensed advisors.
      </div>
    </aside>
  )
}

/* ─── Main export ──────────────────────────────────────────────────────── */

export function ChatView() {
  const [searchParams] = useSearchParams()
  const bootstrapSessionId = searchParams.get('bootstrap')
  const navigate = useNavigate()

  const {
    sessionId, messages, pendingTool, streamState, errorMessage,
    setSession, appendUserMessage, setPendingTool, setStreamState, loadSession,
  } = useChatStore()

  const { stream, abort } = useChatStream()

  const didBootstrapRef = useRef(false)

  useEffect(() => {
    if (!bootstrapSessionId || didBootstrapRef.current) return
    didBootstrapRef.current = true
    setSession(bootstrapSessionId)
    stream(bootstrapSessionId, { type: 'user_message', content: '__bootstrap__', idempotency_key: newIk() })
    return abort
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootstrapSessionId])

  const didResumeRef = useRef(false)
  const [resuming, setResuming] = useState(!bootstrapSessionId)

  useEffect(() => {
    if (bootstrapSessionId || sessionId || didResumeRef.current) return
    didResumeRef.current = true

    async function resume() {
      try {
        const list = await getSessions()
        if (!list.length) { navigate('/onboard', { replace: true }); return }
        const detail = await getSession(list[0].session_id)
        loadSession(detail)
      } catch (err) {
        console.error('[ChatView resume]', err)
      } finally {
        setResuming(false)
      }
    }
    resume()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSend(text: string) {
    if (!sessionId) return
    if (pendingTool) {
      await stream(sessionId, { type: 'tool_approval', tool_use_id: pendingTool.tool_use_id, decision: 'deny', feedback: 'User sent a new message.', idempotency_key: newIk() })
      setPendingTool(null)
    }
    const msgId = crypto.randomUUID()
    appendUserMessage({ id: msgId, role: 'user', content: text })
    stream(sessionId, { type: 'user_message', content: text, idempotency_key: newIk() })
  }

  async function handleApprove(overrides?: { amount_eur?: number }) {
    if (!sessionId || !pendingTool) return
    const body: TurnRequest = { type: 'tool_approval', tool_use_id: pendingTool.tool_use_id, decision: 'approve', overrides, idempotency_key: newIk() }
    setPendingTool(null)
    stream(sessionId, body)
  }

  async function handleDeny(feedback?: string) {
    if (!sessionId || !pendingTool) return
    const body: TurnRequest = { type: 'tool_approval', tool_use_id: pendingTool.tool_use_id, decision: 'deny', feedback, idempotency_key: newIk() }
    setPendingTool(null)
    stream(sessionId, body)
  }

  if (resuming) {
    return (
      <div style={cs.page}>
        <ChatSidebar />
        <div style={{ ...cs.main, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="loader" size={24} color="var(--violet-2)"/>
        </div>
      </div>
    )
  }

  return (
    <div style={cs.page}>
      <ChatSidebar />
      <div style={cs.main}>
        {/* Top bar */}
        <div style={cs.topbar}>
          <div style={cs.coachBadge}>
            <div style={cs.coachAvatar}><Icon name="bunq" size={20} stroke={2}/></div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.2 }}>Nest coach</div>
              <div style={{ fontSize: 12, color: 'var(--violet-2)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--violet-2)', display: 'inline-block' }}/>
                Live &middot; powered by Claude Sonnet
              </div>
            </div>
          </div>
          <button onClick={() => navigate('/')} style={{
            fontSize: 13, color: 'var(--ink-3)', padding: '8px 14px',
            border: '1px solid var(--line)', borderRadius: 999,
            background: 'rgba(255,255,255,0.04)', cursor: 'pointer',
          }}>Start over</button>
        </div>

        {/* Messages */}
        <MessageList messages={messages} />

        {/* Approval */}
        {pendingTool && (
          <div style={{ padding: '0 28px 10px', maxWidth: 760, margin: '0 auto', width: '100%' }}>
            <ApprovalCard
              proposal={pendingTool}
              disabled={streamState === 'streaming'}
              onApprove={handleApprove}
              onDeny={handleDeny}
            />
          </div>
        )}

        {/* Error */}
        {errorMessage && streamState === 'error' && (
          <div style={{
            margin: '0 28px 8px', padding: '10px 14px', borderRadius: 12,
            background: 'rgba(251,113,133,0.1)', color: 'var(--terracotta)',
            fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            maxWidth: 760, marginLeft: 'auto', marginRight: 'auto',
          }}>
            <span>{errorMessage}</span>
            <button style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', textDecoration: 'underline', fontSize: 13 }}
              onClick={() => setStreamState('idle')}>dismiss</button>
          </div>
        )}

        {/* Composer */}
        <Composer streamState={streamState} onSend={handleSend} />
      </div>
      <HandoffCTAConnected />
    </div>
  )
}
