import { useRef } from 'react'
import { postTurn } from '@/api/chat'
import type { SseEvent, TurnRequest } from '@/api/types'
import { useChatStore } from './chatStore'

// Parses a single SSE block after normalizing CRLF to LF line endings.
function parseSseBlock(block: string): SseEvent | null {
  const lines = block.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')
  let event = ''
  let data  = ''
  for (const line of lines) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    if (line.startsWith('data:'))  data  = line.slice(5).trim()
  }
  if (!event || !data) return null
  try {
    return { event, data: JSON.parse(data) } as SseEvent
  } catch {
    return null
  }
}

export function useChatStream() {
  const abortRef = useRef<AbortController | null>(null)
  const store    = useChatStore()

  async function stream(sessionId: string, body: TurnRequest) {
    abortRef.current?.abort()
    const abort = new AbortController()
    abortRef.current = abort

    store.setStreamState('streaming')
    store.setError(null)

    // Each assistant turn gets a stable id for delta accumulation.
    const assistantMsgId = crypto.randomUUID()
    store.startAssistantMessage(assistantMsgId)

    let streamFinalized = false

    function finalizeOnce(state: 'idle' | 'error' | 'awaiting_approval', errorMsg?: string) {
      if (streamFinalized) return
      streamFinalized = true
      if (errorMsg) store.setError(errorMsg)
      store.setStreamState(state)
      store.finaliseAssistantMessage(assistantMsgId)
    }

    try {
      const res = await postTurn(sessionId, body, abort.signal)
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

        let idx: number
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          const ev = parseSseBlock(block)
          if (!ev) continue
          handleEvent(ev, assistantMsgId, finalizeOnce)
        }
      }

      // Stream closed without a done/error event — recover from frozen state.
      finalizeOnce('idle')
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      finalizeOnce('error', 'Connection lost. Tap to retry.')
    }
  }

  function handleEvent(
    ev: SseEvent,
    assistantMsgId: string,
    finalizeOnce: (state: 'idle' | 'error' | 'awaiting_approval', errorMsg?: string) => void,
  ) {
    switch (ev.event) {
      case 'delta':
        store.appendDelta(assistantMsgId, ev.data.text)
        break

      case 'tool_call':
        // Tool pills are rendered from the message's tool_calls array.
        useChatStore.setState((s) => {
          const messages = [...s.messages]
          const last = messages.findLast((m) => m.id === assistantMsgId)
          if (!last) return {}
          const tool_calls = [
            ...(last.tool_calls ?? []),
            { tool_use_id: ev.data.tool_use_id, name: ev.data.name, params: ev.data.params },
          ]
          return { messages: messages.map((m) => (m.id === assistantMsgId ? { ...m, tool_calls } : m)) }
        })
        break

      case 'tool_result':
        store.setToolResult(ev.data.tool_use_id, ev.data.ok, ev.data.summary, ev.data.error)
        break

      case 'tool_proposal':
        store.setPendingTool(ev.data)
        break

      case 'done':
        finalizeOnce(ev.data.reason === 'awaiting_approval' ? 'awaiting_approval' : 'idle')
        break

      case 'error':
        finalizeOnce('error', ev.data.message)
        break
    }
  }

  function abort() {
    abortRef.current?.abort()
  }

  return { stream, abort }
}
