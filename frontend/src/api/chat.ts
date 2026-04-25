import { apiFetch } from './client'
import type { TurnRequest, SessionDetail, Message, ToolName, ProfileSnapshot } from './types'

export async function postTurn(sessionId: string, body: TurnRequest, signal?: AbortSignal): Promise<Response> {
  return apiFetch(`/chat/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { Accept: 'text/event-stream' },
    signal,
  })
}

// Backend turn shape (from Turn.model_dump())
type RawTurn = {
  turn_id: string
  session_id: string
  ts_ms: number
  kind: 'user_message' | 'assistant_message' | 'tool_result' | 'tool_approval'
  content: string | null
  tool_uses: { tool_use_id: string; name: string; params?: object }[] | null
  hidden: boolean
}

/**
 * Convert raw backend turns into the frontend Message[] shape.
 */
function turnsToMessages(turns: RawTurn[]): Message[] {
  const messages: Message[] = []
  for (const t of turns) {
    if (t.kind === 'user_message') {
      messages.push({
        id: t.turn_id,
        role: 'user',
        content: t.content ?? '',
        streaming: false,
        tool_calls: [],
      })
    } else if (t.kind === 'assistant_message') {
      messages.push({
        id: t.turn_id,
        role: 'assistant',
        content: t.content ?? '',
        streaming: false,
        tool_calls: (t.tool_uses ?? []).map((tu) => ({
          tool_use_id: tu.tool_use_id,
          name: tu.name as ToolName,
          params: tu.params ?? {},
        })),
      })
    }
  }
  return messages
}

export async function getSessions(): Promise<{ session_id: string; started_at: number }[]> {
  const res = await apiFetch('/chat/sessions')
  if (!res.ok) throw new Error(`sessions list ${res.status}`)
  const body = await res.json() as { sessions: { session_id: string; started_at: number }[] }
  return body.sessions
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const res = await apiFetch(`/chat/sessions/${sessionId}`)
  if (!res.ok) throw new Error(`session detail ${res.status}`)
  const body = await res.json() as {
    session: { session_id: string; user_id: string }
    turns: RawTurn[]
  }
  return {
    session_id: body.session.session_id,
    profile: null as unknown as SessionDetail['profile'],
    messages: turnsToMessages(body.turns),
    pending_tool: null,
  }
}

export async function updateTarget(
  fundaUrl: string,
  priceOverride?: number,
): Promise<ProfileSnapshot> {
  const res = await apiFetch('/chat/update-target', {
    method: 'POST',
    body: JSON.stringify({
      funda_url: fundaUrl,
      ...(priceOverride != null && { funda_price_override_eur: priceOverride }),
    }),
  })
  if (!res.ok) throw new Error(`update-target ${res.status}`)
  return res.json() as Promise<ProfileSnapshot>
}
