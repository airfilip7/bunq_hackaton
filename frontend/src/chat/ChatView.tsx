import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MessageList } from './MessageList'
import { ApprovalCard } from './ApprovalCard'
import { Composer } from './Composer'
import { useChatStore } from './chatStore'
import { useChatStream } from './useChatStream'
import type { TurnRequest } from '@/api/types'

// Stable UUIDv4 for idempotency — regenerated per message send.
function newIk() { return crypto.randomUUID() }

export function ChatView() {
  const [searchParams] = useSearchParams()
  const bootstrapSessionId = searchParams.get('bootstrap')

  const {
    sessionId,
    messages,
    pendingTool,
    streamState,
    errorMessage,
    setSession,
    appendUserMessage,
    setPendingTool,
    setStreamState,
  } = useChatStore()

  const { stream } = useChatStream()

  // Bootstrap: first session opened from /onboard. No user message needed.
  useEffect(() => {
    if (!bootstrapSessionId) return
    setSession(bootstrapSessionId)
    const body: TurnRequest = {
      type: 'user_message',
      content: '__bootstrap__',  // sentinel; backend skips rendering this as a user turn
      idempotency_key: newIk(),
    }
    stream(bootstrapSessionId, body)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootstrapSessionId])

  // TODO: on mount without bootstrap, load most recent session from GET /chat/sessions.

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

  return (
    <div className="flex flex-col h-screen">
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
