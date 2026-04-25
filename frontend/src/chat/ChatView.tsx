import { useEffect, useRef, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { MessageList } from './MessageList'
import { ApprovalCard } from './ApprovalCard'
import { Composer } from './Composer'
import { useChatStore } from './chatStore'
import { useChatStream } from './useChatStream'
import { PopulatingDashboard } from '@/onboard/PopulatingDashboard'
import { Skeleton } from '@/components/ui/skeleton'
import { getSessions, getSession } from '@/api/chat'
import type { TurnRequest, SessionDetail } from '@/api/types'

// Stable UUIDv4 for idempotency — regenerated per message send.
function newIk() { return crypto.randomUUID() }

export function ChatView() {
  const [searchParams] = useSearchParams()
  const bootstrapSessionId = searchParams.get('bootstrap')

  const navigate = useNavigate()

  const {
    sessionId,
    messages,
    pendingTool,
    streamState,
    errorMessage,
    profile,
    setSession,
    appendUserMessage,
    setPendingTool,
    setStreamState,
    loadSession,
  } = useChatStore()

  const { stream, abort } = useChatStream()

  // Guard prevents StrictMode's double-invoke from firing two requests.
  const didBootstrapRef = useRef(false)

  // Bootstrap: first session opened from /onboard. No user message needed.
  useEffect(() => {
    if (!bootstrapSessionId || didBootstrapRef.current) return
    didBootstrapRef.current = true
    setSession(bootstrapSessionId)
    stream(bootstrapSessionId, {
      type: 'user_message',
      content: '__bootstrap__',
      idempotency_key: newIk(),
    })
    return abort  // cancel stream if component unmounts mid-flight
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootstrapSessionId])

  // Session resume — runs when landing on /chat without a ?bootstrap= param.
  const didResumeRef = useRef(false)
  const [resuming, setResuming] = useState(!bootstrapSessionId)

  useEffect(() => {
    if (bootstrapSessionId || sessionId || didResumeRef.current) return
    didResumeRef.current = true

    async function resume() {
      try {
        const listRes = await getSessions()
        if (!listRes.ok) throw new Error(`sessions list ${listRes.status}`)
        const list = await listRes.json() as { session_id: string }[]

        if (!list.length) {
          navigate('/onboard', { replace: true })
          return
        }

        const detailRes = await getSession(list[0].session_id)
        if (!detailRes.ok) throw new Error(`session detail ${detailRes.status}`)
        const detail = await detailRes.json() as SessionDetail
        loadSession(detail)
      } catch (err) {
        console.error('[ChatView resume]', err)
        // Non-fatal: show empty chat rather than crash.
      } finally {
        setResuming(false)
      }
    }

    resume()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSend(text: string) {
    if (!sessionId) return

    // If there's a pending tool, sending a message = implicit deny + new message.
    if (pendingTool) {
      const denyBody: TurnRequest = {
        type: 'tool_approval',
        tool_use_id: pendingTool.tool_use_id,
        decision: 'deny',
        feedback: 'User sent a new message.',
        idempotency_key: newIk(),
      }
      // Fire-and-forget the denial; the next POST is the real message.
      await stream(sessionId, denyBody)
      setPendingTool(null)
    }

    const msgId = crypto.randomUUID()
    appendUserMessage({ id: msgId, role: 'user', content: text })

    const body: TurnRequest = {
      type: 'user_message',
      content: text,
      idempotency_key: newIk(),
    }
    stream(sessionId, body)
  }

  async function handleApprove(overrides?: { amount_eur?: number }) {
    if (!sessionId || !pendingTool) return
    const body: TurnRequest = {
      type: 'tool_approval',
      tool_use_id: pendingTool.tool_use_id,
      decision: 'approve',
      overrides,
      idempotency_key: newIk(),
    }
    setPendingTool(null)
    stream(sessionId, body)
  }

  async function handleDeny(feedback?: string) {
    if (!sessionId || !pendingTool) return
    const body: TurnRequest = {
      type: 'tool_approval',
      tool_use_id: pendingTool.tool_use_id,
      decision: 'deny',
      feedback,
      idempotency_key: newIk(),
    }
    setPendingTool(null)
    stream(sessionId, body)
  }

  if (resuming) {
    return (
      <div className="flex flex-col h-screen">
        <div className="flex-1 px-4 py-6 flex flex-col gap-4">
          <Skeleton className="h-4 w-2/3 bg-surface-2" />
          <Skeleton className="h-4 w-1/2 bg-surface-2" />
          <Skeleton className="h-4 w-3/4 bg-surface-2" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen">
      {profile && bootstrapSessionId && (
        <div className="px-4 pt-4 pb-2 border-b border-surface-3">
          <PopulatingDashboard profile={profile} />
        </div>
      )}
      <MessageList messages={messages} />

      {/* Approval card sits above the composer */}
      {pendingTool && (
        <div className="px-4 pb-2">
          <ApprovalCard
            proposal={pendingTool}
            disabled={streamState === 'streaming'}
            onApprove={handleApprove}
            onDeny={handleDeny}
          />
        </div>
      )}

      {/* Error banner */}
      {errorMessage && streamState === 'error' && (
        <div className="mx-4 mb-2 px-3 py-2 rounded-lg bg-error/10 text-error text-sm flex justify-between">
          <span>{errorMessage}</span>
          <button
            className="underline"
            onClick={() => setStreamState('idle')}
          >
            dismiss
          </button>
        </div>
      )}

      <Composer streamState={streamState} onSend={handleSend} />
    </div>
  )
}
